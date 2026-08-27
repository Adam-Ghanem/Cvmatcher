from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerateAnalysisActionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UpdateAnalysisActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["todo", "in_progress", "completed"]


class AnalysisActionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    requirement_id: UUID | None = Field(alias="requirementId")
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(min_length=1, max_length=600)
    priority: int = Field(ge=1, le=400)
    category: Literal["must-have", "should-have", "nice-to-have"]
    evidence_state: Literal["NOT_FOUND_IN_PROVIDED_CV"] = Field(alias="evidenceState")
    status: Literal["todo", "in_progress", "completed"]
    position: int = Field(ge=1)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class AnalysisActionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    data: list[AnalysisActionResponse]
    next_cursor: UUID | None = Field(alias="nextCursor")
