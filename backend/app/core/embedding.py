"""Deterministic, dependency-light text embeddings for MOCK mode.

Real mode uses Elasticsearch's own vectorization / a Gemini embedding model. For offline
determinism we hash token n-grams into a fixed-width vector. This is not semantically
perfect, but it is stable, reproducible, and good enough to demonstrate hybrid ranking
and to drive a fully deterministic test suite.
"""
from __future__ import annotations

import hashlib
import math
import re

EMBED_DIM = 64
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def embed(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Return a deterministic unit-length embedding for ``text``."""
    vec = [0.0] * dim
    toks = _tokens(text)
    if not toks:
        return vec
    for tok in toks:
        h = hashlib.sha256(tok.encode("utf-8")).digest()
        for i in range(dim):
            # Use two bytes per dimension for a stable pseudo-random projection.
            byte = h[(i * 2) % len(h)]
            sign = 1.0 if h[(i * 2 + 1) % len(h)] % 2 == 0 else -1.0
            vec[i] += sign * (byte / 255.0)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:  # pragma: no cover - guarded by empty-token check above
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors in [-1, 1]."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
