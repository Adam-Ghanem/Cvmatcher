from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException
from app.models.cv_document import CvDocument, CvDocumentVersion
from app.models.cv_extraction import CvExtraction
from app.models.job_target import JobTarget
from app.models.match_analysis import MatchAnalysis
from app.schemas.match_analyses import (
    CreateMatchAnalysisRequest,
    MatchAnalysisHistoryItem,
    MatchAnalysisHistoryResponse,
    MatchAnalysisResponse,
)
from app.services.cv_extraction import derive_readiness
from app.services.deterministic_scoring import SCORING_VERSION, calculate_deterministic_score


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
        existing = await database_session.scalar(
            select(MatchAnalysis).where(
                MatchAnalysis.cv_document_version_id == version.id,
                MatchAnalysis.job_target_id == target.id,
                MatchAnalysis.scoring_version == SCORING_VERSION,
            )
        )
        if existing is not None:
            return analysis_response(existing)
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
        result = calculate_deterministic_score(extraction.extracted_text, target.job_description)
        overall_score = result["overallScore"]
        if not isinstance(overall_score, int):
            raise RuntimeError("Deterministic scorer returned an invalid overall score.")
        analysis = MatchAnalysis(
            user_id=user_id,
            cv_document_version_id=version.id,
            job_target_id=target.id,
            scoring_version=SCORING_VERSION,
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
        created_at=analysis.created_at,
    )
