from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException
from app.models.cv_document import CvDocument, CvDocumentVersion
from app.models.cv_extraction import CvExtraction
from app.models.job_requirement import JobRequirement
from app.models.job_target import JobTarget
from app.models.match_analysis import MatchAnalysis
from app.schemas.match_analyses import (
    CreateMatchAnalysisRequest,
    MatchAnalysisHistoryItem,
    MatchAnalysisHistoryResponse,
    MatchAnalysisResponse,
)
from app.services.cv_extraction import derive_readiness
from app.services.deterministic_scoring import (
    SCORING_VERSION as SCORING_VERSION_V2,
)
from app.services.deterministic_scoring import (
    calculate_deterministic_score,
)
from app.services.deterministic_scoring_v3 import (
    SCORING_VERSION_V3,
    ReviewedRequirement,
    calculate_deterministic_v3,
)


class MatchAnalysisService:
    async def create_or_get(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        payload: CreateMatchAnalysisRequest,
    ) -> MatchAnalysisResponse:
        version = await database_session.scalar(
            select(CvDocumentVersion)
            .join(CvDocument, CvDocument.id == CvDocumentVersion.document_id)
            .where(
                CvDocumentVersion.id == payload.cv_document_version_id,
                CvDocument.user_id == user_id,
            )
            .with_for_update()
        )
        if version is None:
            raise ApiException("RESOURCE_NOT_FOUND", "We could not find that CV version.", 404)
        target = await database_session.scalar(
            select(JobTarget).where(
                JobTarget.id == payload.job_target_id, JobTarget.user_id == user_id
            )
        )
        if target is None:
            raise ApiException("RESOURCE_NOT_FOUND", "We could not find that target role.", 404)
        extraction = await database_session.scalar(
            select(CvExtraction).where(CvExtraction.document_version_id == version.id)
        )
        if extraction is None:
            raise ApiException(
                "CV_TEXT_NOT_READY",
                "Prepare this CV text before creating an analysis.",
                409,
            )
        readiness = derive_readiness(
            status=extraction.status,
            quality=extraction.quality,
            warnings=extraction.warnings,
        )
        if readiness.state == "blocked" or not extraction.extracted_text:
            raise ApiException(
                "CV_TEXT_NOT_READY",
                "Prepare this CV text before creating an analysis.",
                409,
            )

        if payload.scoring_version == SCORING_VERSION_V2:
            existing = await database_session.scalar(
                select(MatchAnalysis).where(
                    MatchAnalysis.cv_document_version_id == version.id,
                    MatchAnalysis.job_target_id == target.id,
                    MatchAnalysis.scoring_version == SCORING_VERSION_V2,
                )
            )
            if existing is not None:
                return analysis_response(existing)
            input_fingerprint = legacy_v2_input_fingerprint(version.id, target.id)
            result = calculate_deterministic_score(
                extraction.extracted_text,
                target.job_description,
            )
            scoring_version = SCORING_VERSION_V2
        else:
            requirements = tuple(
                reviewed_requirement_from_model(requirement)
                for requirement in (
                    await database_session.scalars(
                        select(JobRequirement)
                        .where(
                            JobRequirement.user_id == user_id,
                            JobRequirement.job_target_id == target.id,
                        )
                        .order_by(JobRequirement.id)
                    )
                ).all()
            )
            input_fingerprint = v3_input_fingerprint(requirements)
            existing = await database_session.scalar(
                select(MatchAnalysis).where(
                    MatchAnalysis.cv_document_version_id == version.id,
                    MatchAnalysis.job_target_id == target.id,
                    MatchAnalysis.scoring_version == SCORING_VERSION_V3,
                    MatchAnalysis.input_fingerprint == input_fingerprint,
                )
            )
            if existing is not None:
                return analysis_response(existing)
            result = calculate_deterministic_v3(
                normalized_cv_terms(extraction.extracted_text),
                requirements,
            )
            calculation_metadata = result.get("calculationMetadata")
            if not isinstance(calculation_metadata, dict):
                raise RuntimeError("Deterministic v3 scorer returned invalid calculation metadata.")
            eligible_requirement_count = calculation_metadata.get("eligibleRequirementCount")
            if eligible_requirement_count == 0:
                raise ApiException(
                    "REQUIREMENTS_NOT_READY",
                    "Add at least one reviewed requirement with a normalized skill "
                    "before analysis.",
                    409,
                )
            calculation_metadata["inputFingerprint"] = input_fingerprint
            scoring_version = SCORING_VERSION_V3

        overall_score = result["overallScore"]
        if not isinstance(overall_score, int):
            raise RuntimeError("Deterministic scorer returned an invalid overall score.")
        analysis = MatchAnalysis(
            user_id=user_id,
            cv_document_version_id=version.id,
            job_target_id=target.id,
            scoring_version=scoring_version,
            input_fingerprint=input_fingerprint,
            overall_score=overall_score,
            result_payload=result,
        )
        database_session.add(analysis)
        await database_session.flush()
        await database_session.refresh(analysis)
        return analysis_response(analysis)

    async def list_history(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        limit: int,
        cursor: UUID | None,
    ) -> MatchAnalysisHistoryResponse:
        cursor_analysis: MatchAnalysis | None = None
        if cursor is not None:
            cursor_analysis = await database_session.scalar(
                select(MatchAnalysis).where(
                    MatchAnalysis.id == cursor,
                    MatchAnalysis.user_id == user_id,
                )
            )
            if cursor_analysis is None:
                raise ApiException("RESOURCE_NOT_FOUND", "We could not find that analysis.", 404)

        history_query = (
            select(
                MatchAnalysis,
                CvDocument.title,
                CvDocumentVersion.version_number,
                JobTarget.title,
            )
            .join(
                CvDocumentVersion,
                CvDocumentVersion.id == MatchAnalysis.cv_document_version_id,
            )
            .join(CvDocument, CvDocument.id == CvDocumentVersion.document_id)
            .join(JobTarget, JobTarget.id == MatchAnalysis.job_target_id)
            .where(
                MatchAnalysis.user_id == user_id,
                CvDocument.user_id == user_id,
                JobTarget.user_id == user_id,
            )
            .order_by(MatchAnalysis.created_at.desc(), MatchAnalysis.id.desc())
            .limit(limit + 1)
        )
        if cursor_analysis is not None:
            history_query = history_query.where(
                or_(
                    MatchAnalysis.created_at < cursor_analysis.created_at,
                    and_(
                        MatchAnalysis.created_at == cursor_analysis.created_at,
                        MatchAnalysis.id < cursor_analysis.id,
                    ),
                )
            )

        rows = (await database_session.execute(history_query)).tuples().all()
        page_rows = rows[:limit]
        items = [
            MatchAnalysisHistoryItem(
                id=analysis.id,
                scoring_version=analysis.scoring_version,
                overall_score=analysis.overall_score,
                cv_document_title=document_title,
                cv_version_number=version_number,
                target_title=target_title,
                created_at=analysis.created_at,
            )
            for analysis, document_title, version_number, target_title in page_rows
        ]
        next_cursor = page_rows[-1][0].id if len(rows) > limit else None
        return MatchAnalysisHistoryResponse(data=items, next_cursor=next_cursor)

    async def get_owned(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        analysis_id: UUID,
    ) -> MatchAnalysisResponse:
        analysis = await database_session.scalar(
            select(MatchAnalysis).where(
                MatchAnalysis.id == analysis_id, MatchAnalysis.user_id == user_id
            )
        )
        if analysis is None:
            raise ApiException("RESOURCE_NOT_FOUND", "We could not find that analysis.", 404)
        return analysis_response(analysis)


def analysis_response(analysis: MatchAnalysis) -> MatchAnalysisResponse:
    payload: dict[str, Any] = analysis.result_payload
    return MatchAnalysisResponse(
        id=analysis.id,
        scoring_version=analysis.scoring_version,
        overall_score=analysis.overall_score,
        components=payload["components"],
        gaps=payload["gaps"],
        requirements=payload.get("requirements"),
        calculation_metadata=payload.get("calculationMetadata"),
        created_at=analysis.created_at,
    )


def reviewed_requirement_from_model(requirement: JobRequirement) -> ReviewedRequirement:
    return ReviewedRequirement(
        requirement_id=str(requirement.id),
        requirement="",
        category=requirement.category,
        normalized_skill=requirement.normalized_skill,
        priority=requirement.priority,
        review_state=requirement.review_state,
        normalization_version=requirement.normalization_version,
    )


def v3_input_fingerprint(requirements: tuple[ReviewedRequirement, ...]) -> str:
    payload = {
        "scoringVersion": SCORING_VERSION_V3,
        "requirements": [
            {
                "id": requirement.requirement_id,
                "category": requirement.category,
                "normalizedSkill": requirement.normalized_skill,
                "priority": requirement.priority,
                "reviewState": requirement.review_state,
                "normalizationVersion": requirement.normalization_version,
            }
            for requirement in requirements
        ],
    }
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def legacy_v2_input_fingerprint(version_id: UUID, target_id: UUID) -> str:
    serialized = f"{SCORING_VERSION_V2}:{version_id}:{target_id}"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def normalized_cv_terms(value: str) -> frozenset[str]:
    from app.services.deterministic_scoring import normalized_terms

    return normalized_terms(value)
