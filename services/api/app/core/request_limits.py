from __future__ import annotations

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import ApiException


class RequestBodyLimitMiddleware:
    """Bound request bytes before parsing while preserving the caller's receive flow."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_request_body_bytes: int,
        max_multipart_request_bytes: int,
    ) -> None:
        self.app = app
        self._max_request_body_bytes = max_request_body_bytes
        self._max_multipart_request_bytes = max_multipart_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = self._request_limit(Headers(scope=scope))
        if self._declared_size_exceeds_limit(Headers(scope=scope), limit):
            raise self._request_too_large_error()

        received_bytes = 0

        async def receive_with_limit() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > limit:
                    raise self._request_too_large_error()
            return message

        await self.app(scope, receive_with_limit, send)

    def _request_limit(self, headers: Headers) -> int:
        if headers.get("content-type", "").lower().startswith("multipart/form-data"):
            return self._max_multipart_request_bytes
        return self._max_request_body_bytes

    @staticmethod
    def _declared_size_exceeds_limit(headers: Headers, limit: int) -> bool:
        content_length = headers.get("content-length")
        if content_length is None:
            return False
        try:
            return int(content_length) > limit
        except ValueError:
            return False

    @staticmethod
    def _request_too_large_error() -> ApiException:
        return ApiException(
            code="REQUEST_TOO_LARGE",
            message="This request is too large to process.",
            status_code=413,
        )
