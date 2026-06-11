"""P5.S2 / C2 — GCP Secret Manager secret resolution.

Skips unless GCP_PROJECT_ID is set AND a Secret Manager provider exists.
"""
from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.integration


def _load_provider():
    try:
        mod = importlib.import_module("app.secrets.gcp_secret_manager")
    except ModuleNotFoundError:
        pytest.skip("Secret Manager provider not implemented yet")
    cls = getattr(mod, "SecretManagerProvider", None)
    if cls is None:
        pytest.skip("Secret Manager provider not implemented yet")
    return cls


async def test_resolve_secret(gcp_env):
    provider_cls = _load_provider()
    provider = provider_cls(project_id=gcp_env["GCP_PROJECT_ID"])
    # Expects a secret named "rover-itest-secret" with a known value in the project.
    value = await provider.get_secret("rover-itest-secret")
    assert isinstance(value, str)
