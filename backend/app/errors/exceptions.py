"""Typed application exceptions mapped to RFC-7807 problem responses.

Each exception carries an HTTP status, a stable ``code`` for clients, and a human title.
The API layer installs a single handler that renders these as ``application/problem+json``.
"""
from __future__ import annotations


class RoverError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    code: str = "internal_error"
    title: str = "Internal Server Error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.title
        super().__init__(self.detail)

    def to_problem(self, instance: str | None = None) -> dict:
        """Render as an RFC-7807 problem document."""
        problem = {
            "type": f"https://errors.crowdcompass/{self.code}",
            "title": self.title,
            "status": self.status_code,
            "code": self.code,
            "detail": self.detail,
        }
        if instance:
            problem["instance"] = instance
        return problem


class UpstreamUnavailableError(RoverError):
    """A required upstream (Elastic MCP / Gemini) is unavailable."""

    status_code = 503
    code = "upstream_unavailable"
    title = "Upstream Service Unavailable"


class RateLimitedError(RoverError):
    """The client exceeded its rate limit."""

    status_code = 429
    code = "rate_limited"
    title = "Too Many Requests"


class AuthenticationError(RoverError):
    """Missing or invalid API key."""

    status_code = 401
    code = "unauthorized"
    title = "Unauthorized"


class ValidationError(RoverError):
    """Domain-level validation failure (distinct from request schema validation)."""

    status_code = 422
    code = "validation_error"
    title = "Validation Error"


class NotFoundError(RoverError):
    """A requested resource does not exist."""

    status_code = 404
    code = "not_found"
    title = "Not Found"
