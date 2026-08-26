from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateMatchAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cv_document_version_id: UUID = Field(alias="cvDocumentVersionId")
    job_target_id: UUID = Field(alias="jobTargetId")
    scoring_version: Literal["deterministic-v2", "deterministic-v3"] = Field(
        default="deterministic-v2",
        alias="scoringVersion",
    )


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
    model_config = ConfigDict(populate_by_name=True)

    term: str
    state: Literal["NOT_FOUND_IN_PROVIDED_CV"]
    component: str
    requirement_id: UUID | None = Field(default=None, alias="requirementId")


class RequirementEvidenceResponse(BaseModel):
    source: Literal["CV_NORMALIZED_SKILL"]
    term: str


class RequirementMatchResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    requirement_id: UUID = Field(alias="requirementId")
    category: Literal["must-have", "should-have", "nice-to-have"]
    normalized_skill: str | None = Field(alias="normalizedSkill")
    priority: int = Field(ge=1, le=100)
    normalization_version: str = Field(alias="normalizationVersion")
    review_state: Literal["unreviewed", "reviewed", "user-confirmed"] = Field(alias="reviewState")
    state: Literal[
        "MATCHED",
        "NOT_FOUND_IN_PROVIDED_CV",
        "NOT_REVIEWED",
        "NOT_COMPARABLE",
        "DUPLICATE_SUPERSEDED",
    ]
    message: str
    evidence: RequirementEvidenceResponse | None


class CalculationMetadataResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    configuration_version: str = Field(alias="configurationVersion")
    category_base_weights: dict[str, int] = Field(alias="categoryBaseWeights")
    eligible_requirement_count: int = Field(alias="eligibleRequirementCount", ge=0)
    input_fingerprint: str = Field(alias="inputFingerprint", min_length=64, max_length=64)


class MatchAnalysisHistoryItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    scoring_version: str = Field(alias="scoringVersion")
    overall_score: int = Field(alias="overallScore", ge=0, le=100)
    cv_document_title: str = Field(alias="cvDocumentTitle")
    cv_version_number: int = Field(alias="cvVersionNumber", ge=1)
    target_title: str = Field(alias="targetTitle")
    created_at: datetime = Field(alias="createdAt")


class MatchAnalysisHistoryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    data: list[MatchAnalysisHistoryItem]
    next_cursor: UUID | None = Field(alias="nextCursor")


class MatchAnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    scoring_version: str = Field(alias="scoringVersion")
    overall_score: int = Field(alias="overallScore", ge=0, le=100)
    components: list[ScoreComponentResponse]
    gaps: list[GapResponse]
    requirements: list[RequirementMatchResponse] | None = None
    calculation_metadata: CalculationMetadataResponse | None = Field(
        default=None,
        alias="calculationMetadata",
    )
    created_at: datetime = Field(alias="createdAt")
