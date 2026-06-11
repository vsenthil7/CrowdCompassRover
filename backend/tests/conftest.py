"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from app.core.config import AppMode, Settings
from app.models.domain import GeoPoint
from app.services.mock_search import MockSearchProvider


@pytest.fixture
def mock_provider() -> MockSearchProvider:
    return MockSearchProvider()


@pytest.fixture
def nyc_location() -> GeoPoint:
    return GeoPoint(lat=40.8135, lon=-74.0745)


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(app_mode=AppMode.MOCK)
