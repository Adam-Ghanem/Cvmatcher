from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApiException(Exception):
    code: str
    message: str
    status_code: int
