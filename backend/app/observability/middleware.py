"""ASGI middleware for request correlation, timing, and access logging.

Assigns a request id (honouring an inbound ``X-Request-ID`` if present), binds it to the
logging context, records latency + status into metrics, and emits a structured access log
line per request.
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.observability.logging_config import get_logger, log_event, request_id_var
from app.observability.metrics import get_metrics

_logger = get_logger("access")


class RequestContextMiddleware:
    """Pure-ASGI middleware (works with streaming responses, unlike BaseHTTPMiddleware)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        inbound = headers.get(b"x-request-id")
        request_id = inbound.decode() if inbound else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        method = scope.get("method", "-")
        path = scope.get("path", "-")
        start = time.perf_counter()
        status_holder = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                hdrs = message.setdefault("headers", [])
                hdrs.append((b"x-request-id", request_id.encode()))
            await send(message)

        metrics = get_metrics()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            status = status_holder["code"]
            metrics.inc(
                "http_requests_total",
                method=method,
                path=path,
                status=str(status),
            )
            metrics.observe("http_request_duration_seconds", elapsed, path=path)
            log_event(
                _logger,
                logging.INFO,
                "request",
                method=method,
                path=path,
                status=status,
                duration_ms=round(elapsed * 1000, 2),
            )
            request_id_var.reset(token)
