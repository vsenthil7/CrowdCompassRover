"""Domain models for CrowdCompass Rover.

These describe the city/event entities indexed in Elasticsearch and the request/response
contracts used by the API and agent layers.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VenueCategory(str, Enum):
    """Category of a city/event point of interest."""

    STADIUM = "stadium"
    RESTAURANT = "restaurant"
    TRANSIT = "transit"
    CURRENCY_EXCHANGE = "currency_exchange"
    FAN_ZONE = "fan_zone"
    HOSPITAL = "hospital"
    HOTEL = "hotel"
    POP_UP_VENDOR = "pop_up_vendor"
    INFO_KIOSK = "info_kiosk"


class GeoPoint(BaseModel):
    """A WGS84 latitude/longitude point."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class CityEvent(BaseModel):
    """A single point of interest / event record in a host city.

    Mirrors the Elasticsearch document mapping: dense ``embedding`` vector for semantic
    retrieval, plus structured fields for ES|QL filters (open-now, distance, category).
    """

    id: str
    name: str
    category: VenueCategory
    city: str
    description: str
    languages: list[str] = Field(default_factory=list)
    location: GeoPoint
    open_now: bool = True
    tags: list[str] = Field(default_factory=list)
    halal: bool = False
    vegetarian: bool = False
    wheelchair_accessible: bool = False
    capacity: int | None = None
    embedding: list[float] | None = None

    def text_blob(self) -> str:
        """Concatenated text used for keyword scoring and mock embedding."""
        return " ".join(
            [self.name, self.description, self.category.value, *self.tags]
        ).lower()


class SearchFilters(BaseModel):
    """Structured filters extracted from a natural-language query."""

    city: str | None = None
    category: VenueCategory | None = None
    open_now: bool | None = None
    halal: bool | None = None
    vegetarian: bool | None = None
    wheelchair_accessible: bool | None = None
    near: GeoPoint | None = None
    max_distance_km: float | None = None


class QueryPlan(BaseModel):
    """The agent's plan for answering a user query.

    Produced by the LLM (or mock planner) from a natural-language, possibly non-English
    question. Drives the hybrid Elasticsearch search.
    """

    original_query: str
    detected_language: str
    normalized_query: str
    semantic_text: str
    filters: SearchFilters = Field(default_factory=SearchFilters)
    top_k: int = Field(default=5, ge=1, le=50)


class ScoredEvent(BaseModel):
    """A search hit with its relevance score and optional distance."""

    event: CityEvent
    score: float
    distance_km: float | None = None


class SearchRequest(BaseModel):
    """Inbound search request from the API."""

    query: str = Field(min_length=1, max_length=2000)
    user_location: GeoPoint | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    session_id: str | None = Field(default=None, max_length=128)
    cursor: str | None = Field(default=None, max_length=256)


class SearchResponse(BaseModel):
    """Search results plus the plan that produced them."""

    plan: QueryPlan
    results: list[ScoredEvent]
    next_cursor: str | None = None
    total: int | None = None


class BatchSearchRequest(BaseModel):
    """Submit several queries in one call."""

    queries: list[str] = Field(min_length=1, max_length=20)
    user_location: GeoPoint | None = None
    top_k: int = Field(default=5, ge=1, le=50)


class ChatRequest(BaseModel):
    """Inbound conversational request (answer is grounded in search results)."""

    query: str = Field(min_length=1, max_length=2000)
    user_location: GeoPoint | None = None
    session_id: str | None = Field(default=None, max_length=128)


class Citation(BaseModel):
    """A grounding citation tying an answer sentence to a source event."""

    event_id: str
    name: str


class ChatAnswer(BaseModel):
    """Final grounded answer payload."""

    answer: str
    language: str
    citations: list[Citation]
    results: list[ScoredEvent]


class RouteRequest(BaseModel):
    """Inbound route-enrichment request ('cheapest route to the stadium')."""

    origin: GeoPoint
    destination: GeoPoint
    modes: list[str] | None = Field(default=None)


class SavedSearchRequest(BaseModel):
    """Create a saved search."""

    owner: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=2000)
    label: str = Field(min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list)


class WebhookRequest(BaseModel):
    """Register a webhook subscription."""

    tenant: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=2000)
    secret: str = Field(min_length=8, max_length=256)
    events: list[str] = Field(min_length=1, max_length=20)
