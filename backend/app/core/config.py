"""Typed application settings, loaded once at startup.

A single ``APP_MODE`` drives whether integrations talk to real services or to the
deterministic offline mocks. This keeps 100% of the pipeline testable in CI while
remaining real-credential-ready (see docs/00-ACCESS-REQUIREMENTS.md).
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppMode(str, Enum):
    """Runtime integration mode."""

    MOCK = "mock"
    REAL = "real"
    HYBRID = "hybrid"


class Settings(BaseSettings):
    """Application configuration sourced from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_mode: AppMode = AppMode.MOCK

    # Elasticsearch
    elastic_url: str = ""
    elastic_api_key: str = ""
    elastic_index: str = "cc-city-events"

    # Elastic MCP server
    elastic_mcp_url: str = ""
    elastic_mcp_api_key: str = ""

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Optional
    google_maps_api_key: str = ""

    cors_origins: str = "http://localhost:5173"

    # Security
    api_keys: str = ""  # comma-separated; empty disables auth
    # When true, callers with no/unknown API key get the baseline "visitor" role
    # (search/chat/route/save_search) so public endpoints work zero-config. Elevated
    # routes (analytics, traces, admin, webhooks, gdpr) are always permission-gated.
    rbac_public_baseline: bool = True
    # Live webhook delivery (real/hybrid mode)
    webhook_timeout: float = 5.0
    webhook_allow_http: bool = False
    rate_limit_rate: float = 10.0  # tokens/sec per client
    rate_limit_capacity: float = 20.0

    # Resilience
    retry_max_attempts: int = 3
    circuit_fail_max: int = 5
    circuit_reset_timeout: float = 30.0
    cache_ttl: float = 60.0
    cache_maxsize: int = 512

    # Ranking
    enable_reranking: bool = True
    enable_query_expansion: bool = True
    enable_spell_correction: bool = True

    # Ingestion
    ingest_stale_after: float = 300.0

    # Conversation
    session_ttl: float = 1800.0

    # Concurrency (bulkhead)
    bulkhead_max_concurrent: int = 16
    bulkhead_max_queue: int = 64

    # Retention (seconds): analytics 90d, audit 365d by default
    retention_analytics_seconds: float = 7776000.0
    retention_audit_seconds: float = 31536000.0

    # Observability
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def api_key_set(self) -> set[str]:
        """Configured API keys as a set (empty disables auth)."""
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def elastic_is_real(self) -> bool:
        """Whether the Elastic layer should use the live service."""
        return self.app_mode in (AppMode.REAL, AppMode.HYBRID)

    @property
    def is_live(self) -> bool:
        """Whether the app runs against any live integration (real or hybrid)."""
        return self.app_mode in (AppMode.REAL, AppMode.HYBRID)

    @property
    def llm_is_real(self) -> bool:
        """Whether the LLM/agent layer should use the live Gemini service."""
        return self.app_mode == AppMode.REAL


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
