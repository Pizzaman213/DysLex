"""Request ID middleware — attaches a unique ID to every request/response.

Uses pure ASGI instead of BaseHTTPMiddleware to avoid swallowing
response headers (including CORS) on error paths.
"""

import uuid
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract existing request ID or generate a new one
        request_id: str = ""
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-request-id":
                request_id = header_value.decode("latin-1")
                break
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store on scope so downstream code can access via request.state
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_wrapper(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
