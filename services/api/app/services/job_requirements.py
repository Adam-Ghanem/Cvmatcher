from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException
from app.models.job_requirement import JobRequirement
from app.models.job_target import JobTarget
from app.schemas.job_requirements import (
    CreateJobRequirementRequest,
    JobRequirementListResponse,
    JobRequirementResponse,
    UpdateJobRequirementRequest,
)

MANUAL_NORMALIZATION_VERSION = "manual-v1"


class JobRequirementService:
    async def create_requirement(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        target_id: UUID,
        payload: CreateJobRequirementRequest,
    ) -> JobRequirementResponse:
        await get_owned_target(database_session, user_id=user_id, target_id=target_id)
        requirement = JobRequirement(
            user_id=user_id,
            job_target_id=target_id,
            requirement_text=payload.requirement,
            category=payload.category,
            normalized_skill=normalize_skill(payload.normalized_skill),
            priority=payload.priority,
            source_reference=empty_to_none(payload.source_reference),
            normalization_version=MANUAL_NORMALIZATION_VERSION,
            review_state=payload.review_state,
        )
        database_session.add(requirement)
        await database_session.flush()
        await database_session.refresh(requirement)
        return requirement_response(requirement)

    async def list_requirements(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        target_id: UUID,
        limit: int,
        cursor: UUID | None,
    ) -> JobRequirementListResponse:
        await get_owned_target(database_session, user_id=user_id, target_id=target_id)
        cursor_requirement: JobRequirement | None = None
        if cursor is not None:
            cursor_requirement = await get_owned_requirement(
                database_session,
                user_id=user_id,
                target_id=target_id,
                requirement_id=cursor,
            )

        requirements_query = (
            select(JobRequirement)
            .where(
                JobRequirement.user_id == user_id,
                JobRequirement.job_target_id == target_id,
            )
            .order_by(
                JobRequirement.priority.desc(),
                JobRequirement.created_at.desc(),
                JobRequirement.id.desc(),
            )
            .limit(limit + 1)
        )
        if cursor_requirement is not None:
            requirements_query = requirements_query.where(
                or_(
                    JobRequirement.priority < cursor_requirement.priority,
                    and_(
                        JobRequirement.priority == cursor_requirement.priority,
                        JobRequirement.created_at < cursor_requirement.created_at,
                    ),
                    and_(
                        JobRequirement.priority == cursor_requirement.priority,
                        JobRequirement.created_at == cursor_requirement.created_at,
                        JobRequirement.id < cursor_requirement.id,
                    ),
                )
            )

        rows = (await database_session.scalars(requirements_query)).all()
        page = rows[:limit]
        next_cursor = page[-1].id if len(rows) > limit else None
        return JobRequirementListResponse(
            data=[requirement_response(requirement) for requirement in page],
            next_cursor=next_cursor,
        )

    async def update_requirement(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        target_id: UUID,
        requirement_id: UUID,
        payload: UpdateJobRequirementRequest,
    ) -> JobRequirementResponse:
        requirement = await get_owned_requirement(
            database_session,
            user_id=user_id,
            target_id=target_id,
            requirement_id=requirement_id,
            lock=True,
        )
        fields = payload.model_fields_set
        if "requirement" in fields:
            if payload.requirement is None:
                raise RuntimeError(
                    "Validated requirement update unexpectedly omitted requirement text."
                )
            requirement.requirement_text = payload.requirement
        if "category" in fields:
            if payload.category is None:
                raise RuntimeError("Validated requirement update unexpectedly omitted category.")
            requirement.category = payload.category
        if "normalized_skill" in fields:
            requirement.normalized_skill = normalize_skill(payload.normalized_skill)
        if "priority" in fields:
            if payload.priority is None:
                raise RuntimeError("Validated requirement update unexpectedly omitted priority.")
            requirement.priority = payload.priority
        if "source_reference" in fields:
            requirement.source_reference = empty_to_none(payload.source_reference)
        if "review_state" in fields:
            if payload.review_state is None:
                raise RuntimeError(
                    "Validated requirement update unexpectedly omitted review state."
                )
            requirement.review_state = payload.review_state
        await database_session.flush()
        await database_session.refresh(requirement)
        return requirement_response(requirement)

    async def delete_requirement(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        target_id: UUID,
        requirement_id: UUID,
    ) -> None:
        requirement = await get_owned_requirement(
            database_session,
            user_id=user_id,
            target_id=target_id,
            requirement_id=requirement_id,
            lock=True,
        )
        await database_session.delete(requirement)
        await database_session.flush()


async def get_owned_target(
    database_session: AsyncSession,
    *,
    user_id: UUID,
    target_id: UUID,
) -> JobTarget:
    target = await database_session.scalar(
        select(JobTarget).where(JobTarget.id == target_id, JobTarget.user_id == user_id)
    )
    if target is None:
        raise ApiException("RESOURCE_NOT_FOUND", "We could not find that target role.", 404)
    return target


async def get_owned_requirement(
    database_session: AsyncSession,
    *,
    user_id: UUID,
    target_id: UUID,
    requirement_id: UUID,
    lock: bool = False,
) -> JobRequirement:
    query = select(JobRequirement).where(
        JobRequirement.id == requirement_id,
        JobRequirement.user_id == user_id,
        JobRequirement.job_target_id == target_id,
    )
    if lock:
        query = query.with_for_update()
    requirement = await database_session.scalar(query)
    if requirement is None:
        raise ApiException("RESOURCE_NOT_FOUND", "We could not find that job requirement.", 404)
    return requirement


def normalize_skill(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.casefold().split())
    return normalized or None


def empty_to_none(value: str | None) -> str | None:
    return value or None


def requirement_response(requirement: JobRequirement) -> JobRequirementResponse:
    return JobRequirementResponse(
        id=requirement.id,
        requirement=requirement.requirement_text,
        category=requirement.category,
        normalized_skill=requirement.normalized_skill,
        priority=requirement.priority,
        source_reference=requirement.source_reference,
        normalization_version=requirement.normalization_version,
        review_state=requirement.review_state,
        created_at=requirement.created_at,
        updated_at=requirement.updated_at,
    )
