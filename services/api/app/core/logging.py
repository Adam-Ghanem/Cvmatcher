from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "authorization",
        "cookie",
        "cvcontent",
        "cvtext",
        "documentcontent",
        "email",
        "extractedtext",
        "filename",
        "jobdescription",
        "jobtext",
        "objectkey",
        "openaapikey",
        "originalfilename",
        "password",
        "privateobjectkey",
        "secret",
        "sessiontoken",
        "csrftoken",
        "token",
    }
)


def normalized_field_name(value: object) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]"
            if normalized_field_name(key) in SENSITIVE_FIELD_NAMES
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_context.get()
        if request_id:
            event["request_id"] = request_id
        if hasattr(record, "event"):
            event["event"] = redact(record.event)
        return json.dumps(event, default=str)


# These libraries can log full request targets, including query strings. Application
# middleware emits a deliberately bounded request-completion event instead.
REQUEST_TARGET_LOGGERS = ("httpx", "httpcore", "uvicorn.access")


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    for logger_name in REQUEST_TARGET_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
