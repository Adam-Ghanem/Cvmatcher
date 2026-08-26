from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateMatchAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cv_document_version_id: UUID = Field(alias="cvDocumentVersionId")
    job_target_id: UUID = Field(alias="jobTargetId")


class ScoreComponentResponse(BaseModel):
    key: str
    label: str
    weight: int
    score: int = Field(ge=0, le=100)
    state: Literal["MATCHED", "PARTIAL", "EVIDENCE_NOT_FOUND", "NOT_APPLICABLE"]
    matched_terms: list[str] = Field(alias="matchedTerms")
    not_found_terms: list[str] = Field(alias="notFoundTerms")
    explanation: str


class GapResponse(BaseModel):
    term: str
    state: Literal["NOT_FOUND_IN_PROVIDED_CV"]
    component: str


class MatchAnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    scoring_version: str = Field(alias="scoringVersion")
    overall_score: int = Field(alias="overallScore", ge=0, le=100)
    components: list[ScoreComponentResponse]
    gaps: list[GapResponse]
    created_at: datetime = Field(alias="createdAt")
