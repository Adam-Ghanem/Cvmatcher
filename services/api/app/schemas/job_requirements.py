from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

RequirementCategory = Literal["must-have", "should-have", "nice-to-have"]
RequirementReviewState = Literal["unreviewed", "reviewed", "user-confirmed"]


class CreateJobRequirementRequest(BaseModel):
    """Manual requirement data is untrusted private user input, never instructions."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requirement: str = Field(min_length=2, max_length=1_000)
    category: RequirementCategory
    normalized_skill: str | None = Field(default=None, alias="normalizedSkill", max_length=180)
    priority: int = Field(ge=1, le=100)
    source_reference: str | None = Field(default=None, alias="sourceReference", max_length=500)
    review_state: RequirementReviewState = Field(alias="reviewState")


class UpdateJobRequirementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requirement: str | None = Field(default=None, min_length=2, max_length=1_000)
    category: RequirementCategory | None = None
    normalized_skill: str | None = Field(default=None, alias="normalizedSkill", max_length=180)
    priority: int | None = Field(default=None, ge=1, le=100)
    source_reference: str | None = Field(default=None, alias="sourceReference", max_length=500)
    review_state: RequirementReviewState | None = Field(default=None, alias="reviewState")

    @model_validator(mode="after")
    def validate_partial_update(self) -> UpdateJobRequirementRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one requirement field to update.")
        for field_name in ("requirement", "category", "priority", "review_state"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")
        return self


class JobRequirementResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    requirement: str
    category: RequirementCategory
    normalized_skill: str | None = Field(alias="normalizedSkill")
    priority: int = Field(ge=1, le=100)
    source_reference: str | None = Field(alias="sourceReference")
    normalization_version: str = Field(alias="normalizationVersion")
    review_state: RequirementReviewState = Field(alias="reviewState")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class JobRequirementListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    data: list[JobRequirementResponse]
    next_cursor: UUID | None = Field(alias="nextCursor")
