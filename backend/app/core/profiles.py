"""Environment profiles and settings validation.

Provides named profiles (dev / staging / prod) that express sensible defaults and a
validator that flags unsafe combinations (e.g. real mode without credentials, prod with
auth disabled). The validator returns structured issues rather than raising, so callers
can log warnings or fail fast as appropriate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from app.core.config import AppMode, Settings


class Profile(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Severity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A single configuration problem."""

    severity: Severity
    field: str
    message: str


@dataclass
class ValidationResult:
    """Outcome of validating settings against a profile."""

    profile: Profile
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when there are no ERROR-severity issues."""
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]


def validate_settings(settings: Settings, profile: Profile) -> ValidationResult:
    """Validate settings for a deployment profile."""
    result = ValidationResult(profile=profile)

    # Real Elastic requires MCP credentials.
    if settings.elastic_is_real and not (
        settings.elastic_mcp_url and settings.elastic_mcp_api_key
    ):
        result.issues.append(
            ValidationIssue(
                Severity.ERROR,
                "elastic_mcp_url",
                "real/hybrid mode requires Elastic MCP url and api key",
            )
        )

    # Real LLM requires a Gemini key.
    if settings.llm_is_real and not settings.gemini_api_key:
        result.issues.append(
            ValidationIssue(
                Severity.ERROR, "gemini_api_key", "real mode requires a Gemini API key"
            )
        )

    if profile == Profile.PROD:
        if settings.app_mode == AppMode.MOCK:
            result.issues.append(
                ValidationIssue(
                    Severity.ERROR, "app_mode", "production must not run in mock mode"
                )
            )
        if not settings.api_key_set:
            result.issues.append(
                ValidationIssue(
                    Severity.ERROR, "api_keys", "production requires API key authentication"
                )
            )
        if "localhost" in settings.cors_origins or "127.0.0.1" in settings.cors_origins:
            result.issues.append(
                ValidationIssue(
                    Severity.WARNING, "cors_origins", "localhost CORS origin in production"
                )
            )

    if profile == Profile.STAGING and not settings.api_key_set:
        result.issues.append(
            ValidationIssue(
                Severity.WARNING, "api_keys", "staging without API keys is discouraged"
            )
        )

    return result
