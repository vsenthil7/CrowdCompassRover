"""Query expansion: synonyms and multilingual term broadening.

Expands the semantic text with domain synonyms so a search for "metro" also matches
"subway"/"underground", "food" matches "restaurant"/"eat", etc. Expansion is additive and
bounded to avoid diluting relevance.
"""
from __future__ import annotations

_SYNONYMS: dict[str, list[str]] = {
    "metro": ["subway", "underground", "train", "rail"],
    "subway": ["metro", "underground", "train"],
    "train": ["rail", "metro", "subway"],
    "food": ["restaurant", "eat", "dining", "meal"],
    "restaurant": ["food", "dining", "eat"],
    "eat": ["food", "restaurant", "dining"],
    "money": ["currency", "exchange", "cash", "forex"],
    "currency": ["money", "exchange", "forex"],
    "exchange": ["currency", "money", "forex"],
    "stadium": ["arena", "ground", "venue", "pitch"],
    "route": ["directions", "way", "path", "transit"],
    "cheap": ["budget", "affordable", "low-cost"],
    "fan": ["supporter", "festival", "celebration"],
}

# Cap on synonyms added per token to keep precision.
_MAX_PER_TOKEN = 3


def expand_terms(text: str) -> str:
    """Return the text augmented with bounded synonyms (deduplicated, order-stable)."""
    tokens = text.lower().split()
    seen: set[str] = set(tokens)
    expanded: list[str] = list(tokens)
    for tok in tokens:
        for syn in _SYNONYMS.get(tok, [])[:_MAX_PER_TOKEN]:
            if syn not in seen:
                seen.add(syn)
                expanded.append(syn)
    return " ".join(expanded)


def synonyms_for(token: str) -> list[str]:
    """Return the known synonyms for a single token."""
    return list(_SYNONYMS.get(token.lower(), []))
