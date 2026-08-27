from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit_events import record_audit_event
from app.tests.conftest import sync_database_url
from app.tests.test_analysis_actions import (
    create_v3_analysis_with_requirements,
    generate_actions,
)
from app.tests.test_authentication import csrf_token, register


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, instance: object) -> None:
        self.added.append(instance)


def persisted_audit_events() -> list[dict[str, Any]]:
    engine = create_engine(sync_database_url())
    try:
        with engine.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT event_type, user_id, request_id, metadata_json "
                        "FROM audit_events ORDER BY created_at, id"
                    )
                ).mappings()
            ]
    finally:
        engine.dispose()


def test_audit_event_service_rejects_non_allowlisted_or_non_scalar_metadata() -> None:
    database_session = RecordingSession()

    with pytest.raises(ValueError, match="Unsupported audit event type"):
        record_audit_event(
            cast(AsyncSession, database_session),
            event_type="cv.raw_content_logged",
            user_id=uuid4(),
            metadata={},
        )
    with pytest.raises(ValueError, match="Unexpected audit event metadata fields"):
        record_audit_event(
            cast(AsyncSession, database_session),
            event_type="analysis.created",
            user_id=uuid4(),
            metadata={"cv_text": "private"},
        )
    with pytest.raises(ValueError, match="bounded scalar value"):
        record_audit_event(
            cast(AsyncSession, database_session),
            event_type="action_plan.generated",
            user_id=uuid4(),
            metadata=cast(dict[str, Any], {"created_count": []}),
        )

    assert database_session.added == []


def test_core_lifecycle_records_fixed_non_content_audit_events(client: TestClient) -> None:
    register(client, "audit-events@example.com")
    _, _, _, analysis_id, _ = create_v3_analysis_with_requirements(client)
    generated = generate_actions(client, analysis_id)
    action = cast(dict[str, object], generated.json()["data"][0])
    updated = client.patch(
        f"/api/v1/match-analyses/{analysis_id}/actions/{action['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"status": "completed"},
    )
    events = persisted_audit_events()
    serialized_events = json.dumps(events, default=str, sort_keys=True)
    event_types = {event["event_type"] for event in events}

    assert generated.status_code == 201
    assert updated.status_code == 200
    assert {
        "auth.account_created",
        "auth.session_issued",
        "cv.extraction_succeeded",
        "analysis.created",
        "action_plan.generated",
        "action.status_updated",
    }.issubset(event_types)
    assert all(event["user_id"] is not None for event in events)
    assert all(event["request_id"] is not None for event in events)
    assert "CV_PRIVATE_EVIDENCE_MARKER" not in serialized_events
    assert "Private platform target" not in serialized_events
    assert "private_object_key" not in serialized_events
    assert "requirement_text" not in serialized_events
    assert "example-password" not in serialized_events


def test_audit_events_store_only_allowlisted_scalar_metadata(client: TestClient) -> None:
    register(client, "audit-metadata@example.com")
    _, _, _, analysis_id, _ = create_v3_analysis_with_requirements(client)
    generate_actions(client, analysis_id)
    events = persisted_audit_events()

    for event in events:
        metadata = event["metadata_json"]
        assert isinstance(metadata, dict)
        assert all(isinstance(key, str) for key in metadata)
        assert all(isinstance(value, (str, int, bool, type(None))) for value in metadata.values())
