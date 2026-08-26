from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class CredentialsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().casefold()
        if not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Enter a valid email address.")
        return email

    @field_validator("password")
    @classmethod
    def reject_whitespace_only_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must not be empty.")
        return value


class PublicUser(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: UUID
    email: str
    created_at: datetime = Field(alias="createdAt")


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: PublicUser


class CsrfTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    csrf_token: str = Field(alias="csrfToken", min_length=32, max_length=128)
