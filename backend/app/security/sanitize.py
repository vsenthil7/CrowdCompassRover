"""Input hardening: sanitisation and abuse guards beyond schema validation.

Pydantic validates shape; this layer defends meaning. It strips control characters,
collapses pathological whitespace, caps token counts, neutralises obvious injection
markers, and flags abusive patterns (excessive repetition). Returns a cleaned string plus
a list of applied actions for observability.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WS_RE = re.compile(r"\s+")
# Markers sometimes used to attempt prompt/DSL injection; we neutralise rather than reject.
_INJECTION_MARKERS = ("```", "</", "<script", "${", "{{", "system:", "ignore previous")
MAX_TOKENS = 64
MAX_LENGTH = 2000


@dataclass
class Sanitised:
    """Result of sanitising an input string."""

    value: str
    actions: list[str] = field(default_factory=list)
    flagged: bool = False


def _strip_control(text: str) -> str:
    return _CONTROL_RE.sub("", text)


def sanitize_query(raw: str) -> Sanitised:
    """Clean and harden a free-text query."""
    actions: list[str] = []
    flagged = False

    text = unicodedata.normalize("NFKC", raw)
    if text != raw:
        actions.append("normalized_unicode")

    stripped = _strip_control(text)
    if stripped != text:
        actions.append("removed_control_chars")
    text = stripped

    collapsed = _WS_RE.sub(" ", text).strip()
    if collapsed != text.strip():
        actions.append("collapsed_whitespace")
    text = collapsed

    lowered = text.lower()
    for marker in _INJECTION_MARKERS:
        if marker in lowered:
            text = re.sub(re.escape(marker), " ", text, flags=re.IGNORECASE)
            actions.append("neutralized_injection_marker")
            flagged = True
    if "neutralized_injection_marker" in actions:
        text = _WS_RE.sub(" ", text).strip()

    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH].rstrip()
        actions.append("truncated_length")

    tokens = text.split()
    if len(tokens) > MAX_TOKENS:
        text = " ".join(tokens[:MAX_TOKENS])
        actions.append("truncated_tokens")
        tokens = tokens[:MAX_TOKENS]

    # Abuse: a single token repeated many times.
    if tokens and len(set(tokens)) == 1 and len(tokens) > 5:
        flagged = True
        actions.append("flagged_repetition")

    return Sanitised(value=text, actions=actions, flagged=flagged)
