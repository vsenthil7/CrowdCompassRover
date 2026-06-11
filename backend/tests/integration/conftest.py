"""Shared fixtures + skip logic for live-service integration tests.

Every test in this package is marked ``integration`` and is skipped unless the relevant
credentials are present in the environment. These tests are deselected from the default
coverage run (see ``pyproject.toml``: ``-m "not integration"``); run them explicitly with:

    pytest -m integration tests/integration

or per-service once the matching env vars are set. They never contribute to the 100%
unit-coverage gate and never fabricate a pass — without credentials they skip.
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


def require_env(*names: str) -> dict[str, str]:
    """Return the named env vars, or skip the test if any are missing/empty."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        pytest.skip(f"integration test requires env: {', '.join(missing)}")
    return {n: os.environ[n] for n in names}


@pytest.fixture
def elastic_env() -> dict[str, str]:
    return require_env("ELASTIC_MCP_URL", "ELASTIC_MCP_API_KEY", "ELASTIC_INDEX")


@pytest.fixture
def gemini_env() -> dict[str, str]:
    return require_env("GEMINI_API_KEY")


@pytest.fixture
def gcp_env() -> dict[str, str]:
    return require_env("GCP_PROJECT_ID")


@pytest.fixture
def redis_env() -> dict[str, str]:
    return require_env("REDIS_URL")
