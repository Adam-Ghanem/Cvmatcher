from __future__ import annotations

import pytest
from starlette.types import Message, Receive, Scope, Send

from app.core.errors import ApiException
from app.core.request_limits import RequestBodyLimitMiddleware


@pytest.mark.asyncio
async def test_streamed_request_body_is_rejected_after_crossing_the_non_upload_limit() -> None:
    messages: list[Message] = [
        {"type": "http.request", "body": b"safe", "more_body": True},
        {"type": "http.request", "body": b"-overflow", "more_body": False},
    ]
    received_messages: list[Message] = []

    async def receive() -> Message:
        return messages.pop(0)

    async def send(message: Message) -> None:
        received_messages.append(message)

    async def application(_: Scope, receive: Receive, __: Send) -> None:
        while True:
            message = await receive()
            if not message.get("more_body", False):
                return

    middleware = RequestBodyLimitMiddleware(
        application,
        max_request_body_bytes=8,
        max_multipart_request_bytes=16,
    )

    with pytest.raises(ApiException) as error:
        await middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/auth/login",
                "headers": [],
            },
            receive,
            send,
        )

    assert error.value.code == "REQUEST_TOO_LARGE"
    assert received_messages == []
