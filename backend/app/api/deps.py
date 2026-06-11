"""FastAPI dependency wiring."""
from __future__ import annotations

from app.agent.orchestrator import RoverAgent
from app.analytics.recorder import AnalyticsRecorder
from app.conversation.session import SessionStore
from app.core.config import get_settings
from app.core.providers import Components, build_components
from app.health.checks import HealthRegistry

_components: Components | None = None


def init_components() -> Components:
    """Build and cache components at startup."""
    global _components
    _components = build_components(get_settings())
    return _components


async def shutdown_components() -> None:
    """Close any closable components at shutdown."""
    global _components
    if _components is None:
        return
    for closable in _components.closables:
        aclose = getattr(closable, "aclose", None)
        if aclose is not None:
            await aclose()
    _components = None


def _get_components() -> Components:
    """Return cached components, building them on demand."""
    if _components is None:
        return init_components()
    return _components


def get_agent() -> RoverAgent:
    """Return the constructed agent (FastAPI dependency)."""
    return _get_components().agent


def get_sessions() -> SessionStore:
    """Return the session store (FastAPI dependency)."""
    return _get_components().sessions


def get_analytics() -> AnalyticsRecorder:
    """Return the analytics recorder (FastAPI dependency)."""
    return _get_components().analytics


def get_health_registry() -> HealthRegistry:
    """Return the health registry (FastAPI dependency)."""
    return _get_components().health


def get_tracer():
    """Return the tracer (FastAPI dependency)."""
    return _get_components().tracer


def get_flags():
    """Return the feature-flag registry (FastAPI dependency)."""
    return _get_components().flags


def get_saved_searches():
    """Return the saved-search service (FastAPI dependency)."""
    return _get_components().saved_searches


def get_admin():
    """Return the admin service (FastAPI dependency)."""
    return _get_components().admin


def get_audit():
    """Return the audit log (FastAPI dependency)."""
    return _get_components().audit


def get_webhooks():
    """Return the webhook registry (FastAPI dependency)."""
    return _get_components().webhooks


def get_meter():
    """Return the usage meter (FastAPI dependency)."""
    return _get_components().meter


def get_data_rights():
    """Return the GDPR data-rights service (FastAPI dependency)."""
    return _get_components().data_rights


def get_idempotency():
    """Return the idempotency store (FastAPI dependency)."""
    return _get_components().idempotency


def get_slo():
    """Return the SLO tracker (FastAPI dependency)."""
    return _get_components().slo


def get_versions():
    """Return the API version registry (FastAPI dependency)."""
    return _get_components().versions


def get_outbox():
    """Return the outbox (FastAPI dependency)."""
    return _get_components().outbox


def get_outbox_sink():
    """Return the webhook outbox sink (FastAPI dependency)."""
    return _get_components().outbox_sink


def get_bulkhead():
    """Return the search bulkhead (FastAPI dependency)."""
    return _get_components().bulkhead


def get_retention():
    """Return the retention sweeper (FastAPI dependency)."""
    return _get_components().retention


def get_availability():
    """Return the availability service (FastAPI dependency)."""
    return _get_components().availability


def get_tenants():
    """Return the tenant resolver (FastAPI dependency)."""
    return _get_components().tenants
