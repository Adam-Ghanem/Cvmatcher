from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CvDocumentVersionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID
    version_number: int = Field(alias="versionNumber", ge=1)
    original_filename: str = Field(alias="originalFilename")
    content_type: str = Field(alias="contentType")
    byte_size: int = Field(alias="byteSize", gt=0)
    uploaded_at: datetime = Field(alias="uploadedAt")


class CvDocumentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID
    title: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    latest_version: CvDocumentVersionSummary = Field(alias="latestVersion")


class CvDocumentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[CvDocumentSummary]


class CvDocumentVersionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[CvDocumentVersionSummary]
