"""FastAPI dependency wiring."""
from __future__ import annotations

from app.agent.orchestrator import RoverAgent
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


def get_agent() -> RoverAgent:
    """Return the constructed agent (FastAPI dependency)."""
    if _components is None:
        return init_components().agent
    return _components.agent
