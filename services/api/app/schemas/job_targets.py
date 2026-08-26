from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateJobTargetRequest(BaseModel):
    """Pasted job-description text is untrusted private data, never system instructions."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=2, max_length=180)
    company: str | None = Field(default=None, max_length=180)
    location: str | None = Field(default=None, max_length=180)
    job_description: str = Field(alias="jobDescription", min_length=80, max_length=50_000)


class JobTargetSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    title: str
    company: str | None
    location: str | None
    job_description_character_count: int = Field(alias="jobDescriptionCharacterCount")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class JobTargetListResponse(BaseModel):
    data: list[JobTargetSummary]
