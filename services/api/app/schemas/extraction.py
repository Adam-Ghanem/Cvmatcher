from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CvExtractionReadinessResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    state: Literal["ready", "warning", "blocked"]
    explanation: str
    recovery_guidance: str | None = Field(alias="recoveryGuidance")


class CvExtractionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    status: str
    source_type: str = Field(alias="sourceType")
    character_count: int = Field(alias="characterCount")
    parser_version: str = Field(alias="parserVersion")
    quality: str
    warnings: list[str]
    readiness: CvExtractionReadinessResponse
    completed_at: datetime | None = Field(alias="completedAt")
    failure_message: str | None = Field(alias="failureMessage")
