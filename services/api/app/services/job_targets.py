from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException
from app.models.job_target import JobTarget
from app.schemas.job_targets import CreateJobTargetRequest, JobTargetSummary


class JobTargetService:
    async def create_target(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        payload: CreateJobTargetRequest,
    ) -> JobTargetSummary:
        target = JobTarget(
            user_id=user_id,
            title=payload.title,
            company=empty_to_none(payload.company),
            location=empty_to_none(payload.location),
            job_description=payload.job_description,
            job_description_character_count=len(payload.job_description),
        )
        database_session.add(target)
        await database_session.flush()
        await database_session.refresh(target)
        return job_target_summary(target)

    async def list_targets(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
    ) -> list[JobTargetSummary]:
        result = await database_session.execute(
            select(JobTarget)
            .where(JobTarget.user_id == user_id)
            .order_by(JobTarget.updated_at.desc(), JobTarget.id.desc())
        )
        return [job_target_summary(target) for target in result.scalars()]

    async def delete_target(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        target_id: UUID,
    ) -> None:
        target = await database_session.scalar(
            select(JobTarget)
            .where(JobTarget.id == target_id, JobTarget.user_id == user_id)
            .with_for_update()
        )
        if target is None:
            raise ApiException("RESOURCE_NOT_FOUND", "We could not find that target role.", 404)
        await database_session.delete(target)
        await database_session.flush()

    async def get_target(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        target_id: UUID,
    ) -> JobTargetSummary:
        target = await database_session.scalar(
            select(JobTarget).where(JobTarget.id == target_id, JobTarget.user_id == user_id)
        )
        if target is None:
            raise ApiException("RESOURCE_NOT_FOUND", "We could not find that target role.", 404)
        return job_target_summary(target)


def empty_to_none(value: str | None) -> str | None:
    return value or None


def job_target_summary(target: JobTarget) -> JobTargetSummary:
    return JobTargetSummary(
        id=target.id,
        title=target.title,
        company=target.company,
        location=target.location,
        job_description_character_count=target.job_description_character_count,
        created_at=target.created_at,
        updated_at=target.updated_at,
    )
