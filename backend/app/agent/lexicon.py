"""Lightweight multilingual lexicon for the deterministic mock planner.

Maps intent keywords across several languages to structured filters and English
normalisations. Real mode delegates this to Gemini; the mock keeps it explicit so
multilingual queries are handled deterministically and testably offline.
"""
from __future__ import annotations

from app.models.domain import VenueCategory

# Per-language marker words used for naive language detection.
LANGUAGE_MARKERS: dict[str, list[str]] = {
    "es": ["donde", "estadio", "cerca", "abierto", "comida", "ahora", "barato", "ruta", "cambio"],
    "fr": ["ou", "stade", "pres", "ouvert", "nourriture", "maintenant", "itineraire", "change"],
    "pt": ["onde", "estadio", "perto", "aberto", "comida", "agora", "rota"],
    "de": ["wo", "stadion", "nahe", "offen", "essen", "jetzt", "route"],
    "ar": ["qareeb", "maftuh", "matam", "mahatta"],
    "en": ["where", "stadium", "near", "open", "food", "now", "cheap", "route", "exchange"],
}

# Category trigger terms across languages -> canonical category.
CATEGORY_TERMS: dict[str, VenueCategory] = {
    "stadium": VenueCategory.STADIUM,
    "estadio": VenueCategory.STADIUM,
    "stade": VenueCategory.STADIUM,
    "stadion": VenueCategory.STADIUM,
    "restaurant": VenueCategory.RESTAURANT,
    "food": VenueCategory.RESTAURANT,
    "comida": VenueCategory.RESTAURANT,
    "nourriture": VenueCategory.RESTAURANT,
    "essen": VenueCategory.RESTAURANT,
    "eat": VenueCategory.RESTAURANT,
    "transit": VenueCategory.TRANSIT,
    "train": VenueCategory.TRANSIT,
    "metro": VenueCategory.TRANSIT,
    "subway": VenueCategory.TRANSIT,
    "route": VenueCategory.TRANSIT,
    "ruta": VenueCategory.TRANSIT,
    "itineraire": VenueCategory.TRANSIT,
    "currency": VenueCategory.CURRENCY_EXCHANGE,
    "exchange": VenueCategory.CURRENCY_EXCHANGE,
    "cambio": VenueCategory.CURRENCY_EXCHANGE,
    "change": VenueCategory.CURRENCY_EXCHANGE,
    "forex": VenueCategory.CURRENCY_EXCHANGE,
    "fan": VenueCategory.FAN_ZONE,
    "festival": VenueCategory.FAN_ZONE,
}

# Open-now markers.
OPEN_NOW_TERMS = {"now", "ahora", "maintenant", "agora", "jetzt", "open", "abierto", "ouvert", "maftuh"}

# Dietary markers.
HALAL_TERMS = {"halal"}
VEGETARIAN_TERMS = {"vegetarian", "veggie", "vegetariano", "vegetarien"}

# City markers.
CITY_TERMS: dict[str, str] = {
    "new york": "New York",
    "nyc": "New York",
    "los angeles": "Los Angeles",
    "la": "Los Angeles",
    "mexico city": "Mexico City",
    "mexico": "Mexico City",
    "cdmx": "Mexico City",
}

# Canonical English normalisations for common non-English tokens.
NORMALISE: dict[str, str] = {
    "estadio": "stadium",
    "stade": "stadium",
    "stadion": "stadium",
    "comida": "food",
    "nourriture": "food",
    "essen": "food",
    "cerca": "near",
    "pres": "near",
    "perto": "near",
    "nahe": "near",
    "qareeb": "near",
    "abierto": "open",
    "ouvert": "open",
    "aberto": "open",
    "offen": "open",
    "maftuh": "open",
    "ahora": "now",
    "maintenant": "now",
    "agora": "now",
    "jetzt": "now",
    "barato": "cheap",
    "ruta": "route",
    "itineraire": "route",
    "cambio": "exchange",
    "change": "exchange",
    "donde": "where",
    "ou": "where",
    "onde": "where",
    "wo": "where",
}
