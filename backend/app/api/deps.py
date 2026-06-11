"""FastAPI dependency wiring."""
from __future__ import annotations

from app.agent.orchestrator import RoverAgent
from app.conversation.session import SessionStore
from app.core.config import get_settings
from app.core.providers import Components, build_components

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
