"""Shared-secret access control for a personal deployment.

When ``API_SECRET_KEY`` is set, every HTTP request needs an ``X-API-Key`` header
and every WebSocket needs ``?key=``. ``/health`` CORS pre-flights and OAuth ``/callback`` redirects (which a browser
cannot attach a header to) stay open.
With no key configured the API is open, which is only appropriate on localhost.
"""

from __future__ import annotations

import hmac
import json
from urllib.parse import parse_qs

from src.config.settings import settings

_OPEN_PATHS = {"/health", "/", "/docs", "/openapi.json"}


def _ok(candidate: str | None) -> bool:
    return bool(candidate) and hmac.compare_digest(candidate.encode(), settings.api_secret_key.encode())


class ApiKeyMiddleware:
    """Pure-ASGI so it covers HTTP and WebSocket scopes alike."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        key = settings.api_secret_key
        if not key or scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        if scope["type"] == "http":
            path = scope["path"]
            # The app shell (HTML/JS/CSS) must load so the access-key screen can render;
            # only the API itself is guarded.
            guarded = path.startswith("/api/")
            if (
                scope["method"] == "OPTIONS"
                or not guarded
                or path in _OPEN_PATHS
                or path.endswith("/callback")
            ):
                return await self.app(scope, receive, send)
            headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            if _ok(headers.get("x-api-key")):
                return await self.app(scope, receive, send)
            body = json.dumps({"detail": "Missing or invalid API key"}).encode()
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})
            return

        query = parse_qs(scope.get("query_string", b"").decode())
        if _ok((query.get("key") or [None])[0]):
            return await self.app(scope, receive, send)
        await receive()  # consume websocket.connect
        await send({"type": "websocket.close", "code": 4401})
