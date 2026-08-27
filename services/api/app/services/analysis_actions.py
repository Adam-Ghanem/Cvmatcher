from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException
from app.models.analysis_action import AnalysisAction
from app.models.match_analysis import MatchAnalysis
from app.schemas.analysis_actions import (
    AnalysisActionListResponse,
    AnalysisActionResponse,
    UpdateAnalysisActionRequest,
)
from app.schemas.match_analyses import RequirementMatchResponse
from app.services.audit_events import record_audit_event
from app.services.deterministic_scoring_v3 import SCORING_VERSION_V3

CATEGORY_PRIORITY_BASE = {
    "must-have": 200,
    "should-have": 100,
    "nice-to-have": 0,
}
ACTION_LIST_LIMIT = 50


class AnalysisActionService:
    async def generate_for_analysis(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        analysis_id: UUID,
    ) -> AnalysisActionListResponse:
        analysis = await self._get_owned_analysis(
            database_session,
            user_id=user_id,
            analysis_id=analysis_id,
            lock=True,
        )
        candidates = deterministic_action_candidates(analysis)
        existing_actions = (
            await database_session.scalars(
                select(AnalysisAction).where(
                    AnalysisAction.user_id == user_id,
                    AnalysisAction.analysis_id == analysis.id,
                )
            )
        ).all()
        existing_requirement_ids = {
            action.requirement_id
            for action in existing_actions
            if action.requirement_id is not None
        }
        created_count = 0
        for position, candidate in enumerate(candidates, start=1):
            if candidate.requirement_id in existing_requirement_ids:
                continue
            database_session.add(
                AnalysisAction(
                    user_id=user_id,
                    analysis_id=analysis.id,
                    requirement_id=candidate.requirement_id,
                    title=candidate.title,
                    description=candidate.description,
                    priority=candidate.priority,
                    category=candidate.category,
                    evidence_state=candidate.evidence_state,
                    status="todo",
                    position=position,
                )
            )
            created_count += 1
        record_audit_event(
            database_session,
            event_type="action_plan.generated",
            user_id=user_id,
            metadata={"created_count": created_count},
        )
        await database_session.flush()
        return await self.list_for_analysis(
            database_session,
            user_id=user_id,
            analysis_id=analysis.id,
            limit=ACTION_LIST_LIMIT,
            cursor=None,
        )

    async def list_for_analysis(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        analysis_id: UUID,
        limit: int,
        cursor: UUID | None,
    ) -> AnalysisActionListResponse:
        await self._get_owned_analysis(
            database_session,
            user_id=user_id,
            analysis_id=analysis_id,
            lock=False,
        )
        cursor_action: AnalysisAction | None = None
        if cursor is not None:
            cursor_action = await database_session.scalar(
                select(AnalysisAction).where(
                    AnalysisAction.id == cursor,
                    AnalysisAction.analysis_id == analysis_id,
                    AnalysisAction.user_id == user_id,
                )
            )
            if cursor_action is None:
                raise self._not_found_error()

        query = (
            select(AnalysisAction)
            .where(
                AnalysisAction.analysis_id == analysis_id,
                AnalysisAction.user_id == user_id,
            )
            .order_by(AnalysisAction.position, AnalysisAction.id)
            .limit(limit + 1)
        )
        if cursor_action is not None:
            query = query.where(
                or_(
                    AnalysisAction.position > cursor_action.position,
                    and_(
                        AnalysisAction.position == cursor_action.position,
                        AnalysisAction.id > cursor_action.id,
                    ),
                )
            )
        rows = (await database_session.scalars(query)).all()
        page = rows[:limit]
        return AnalysisActionListResponse(
            data=[action_response(action) for action in page],
            next_cursor=page[-1].id if len(rows) > limit else None,
        )

    async def update_status(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        analysis_id: UUID,
        action_id: UUID,
        payload: UpdateAnalysisActionRequest,
    ) -> AnalysisActionResponse:
        action = await database_session.scalar(
            select(AnalysisAction).where(
                AnalysisAction.id == action_id,
                AnalysisAction.analysis_id == analysis_id,
                AnalysisAction.user_id == user_id,
            )
        )
        if action is None:
            raise self._not_found_error()
        action.status = payload.status
        record_audit_event(
            database_session,
            event_type="action.status_updated",
            user_id=user_id,
            metadata={"status": payload.status},
        )
        await database_session.flush()
        await database_session.refresh(action)
        return action_response(action)

    async def _get_owned_analysis(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        analysis_id: UUID,
        lock: bool,
    ) -> MatchAnalysis:
        query = select(MatchAnalysis).where(
            MatchAnalysis.id == analysis_id,
            MatchAnalysis.user_id == user_id,
        )
        if lock:
            query = query.with_for_update()
        analysis = await database_session.scalar(query)
        if analysis is None:
            raise self._not_found_error()
        return analysis

    @staticmethod
    def _not_found_error() -> ApiException:
        return ApiException("RESOURCE_NOT_FOUND", "We could not find that analysis action.", 404)


class DeterministicActionCandidate:
    def __init__(
        self,
        *,
        requirement_id: UUID,
        title: str,
        description: str,
        priority: int,
        category: str,
        evidence_state: str,
    ) -> None:
        self.requirement_id = requirement_id
        self.title = title
        self.description = description
        self.priority = priority
        self.category = category
        self.evidence_state = evidence_state


def deterministic_action_candidates(
    analysis: MatchAnalysis,
) -> tuple[DeterministicActionCandidate, ...]:
    if analysis.scoring_version != SCORING_VERSION_V3:
        return ()
    requirement_entries = analysis.result_payload.get("requirements")
    if not isinstance(requirement_entries, list):
        raise ApiException(
            "ANALYSIS_ACTIONS_UNAVAILABLE",
            "We could not prepare actions from this analysis.",
            409,
        )
    candidates: list[DeterministicActionCandidate] = []
    for entry in requirement_entries:
        requirement = validated_requirement_entry(entry)
        if requirement.state != "NOT_FOUND_IN_PROVIDED_CV":
            continue
        if requirement.normalized_skill is None:
            continue
        priority = deterministic_action_priority(requirement.category, requirement.priority)
        candidates.append(
            DeterministicActionCandidate(
                requirement_id=requirement.requirement_id,
                title=f"Add evidence for {requirement.normalized_skill}",
                description=(
                    "Update your CV only with truthful, verifiable evidence for "
                    f"{requirement.normalized_skill} if applicable. Evidence was not found in the "
                    "provided CV."
                ),
                priority=priority,
                category=requirement.category,
                evidence_state=requirement.state,
            )
        )
    return tuple(
        sorted(
            candidates,
            key=lambda candidate: (-candidate.priority, str(candidate.requirement_id)),
        )
    )


def validated_requirement_entry(value: object) -> RequirementMatchResponse:
    try:
        return RequirementMatchResponse.model_validate(value)
    except ValidationError as exc:
        raise ApiException(
            "ANALYSIS_ACTIONS_UNAVAILABLE",
            "We could not prepare actions from this analysis.",
            409,
        ) from exc


def deterministic_action_priority(category: str, requirement_priority: int) -> int:
    return CATEGORY_PRIORITY_BASE[category] + requirement_priority


def action_response(action: AnalysisAction) -> AnalysisActionResponse:
    return AnalysisActionResponse(
        id=action.id,
        requirement_id=action.requirement_id,
        title=action.title,
        description=action.description,
        priority=action.priority,
        category=action.category,
        evidence_state=action.evidence_state,
        status=action.status,
        position=action.position,
        created_at=action.created_at,
        updated_at=action.updated_at,
    )
