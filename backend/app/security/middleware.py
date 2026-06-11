"""ASGI middleware enforcing API-key auth and rate limiting.

Runs before routing. Public paths (health, metrics, docs) bypass both checks. Failures are
rendered as problem+json consistent with the error handlers. Pure-ASGI so it composes with
streaming responses.
"""
from __future__ import annotations

import json

from starlette.types import ASGIApp, Receive, Scope, Send

from app.security.auth import ApiKeyAuthenticator
from app.security.rate_limit import TokenBucketRateLimiter

_PUBLIC_PREFIXES = ("/api/health", "/api/ready", "/api/metrics", "/api/version", "/docs", "/openapi.json", "/redoc")


def _problem(status: int, code: str, title: str, path: str) -> bytes:
    return json.dumps(
        {
            "type": f"https://errors.crowdcompass/{code}",
            "title": title,
            "status": status,
            "code": code,
            "detail": title,
            "instance": path,
        }
    ).encode()


class SecurityMiddleware:
    """Enforces authentication and per-client rate limits."""

    def __init__(
        self,
        app: ASGIApp,
        authenticator: ApiKeyAuthenticator,
        limiter: TokenBucketRateLimiter,
    ) -> None:
        self.app = app
        self.auth = authenticator
        self.limiter = limiter

    def _is_public(self, path: str) -> bool:
        return any(path.startswith(p) for p in _PUBLIC_PREFIXES)

    async def _reject(self, send: Send, status: int, code: str, title: str, path: str) -> None:
        body = _problem(status, code, title, path)
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if self._is_public(path):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        api_key = headers.get(b"x-api-key")
        api_key_str = api_key.decode() if api_key else None

        if not self.auth.is_valid(api_key_str):
            await self._reject(send, 401, "unauthorized", "Unauthorized", path)
            return

        client = scope.get("client")
        client_ip = client[0] if client else "anonymous"
        rate_key = api_key_str or client_ip
        if not self.limiter.allow(rate_key):
            await self._reject(send, 429, "rate_limited", "Too Many Requests", path)
            return

        await self.app(scope, receive, send)
