"""Seed / preview the fixture dataset.

In MOCK mode this simply materializes fixtures with embeddings and prints a summary. In
REAL mode (with credentials) this is where bulk indexing into Elasticsearch would run via
the MCP client; that path is left as an explicit TODO gated on access.
"""
from __future__ import annotations

import json

from app.core.embedding import embed
from app.data.fixtures import HOST_CITIES, load_fixture_events


def build_indexable() -> list[dict]:
    """Return fixture docs with embeddings, ready for indexing."""
    events = load_fixture_events()
    docs = []
    for ev in events:
        ev.embedding = embed(ev.text_blob())
        docs.append(ev.model_dump())
    return docs


def main() -> None:  # pragma: no cover - CLI entry
    docs = build_indexable()
    print(f"Host cities: {', '.join(HOST_CITIES)}")
    print(f"Prepared {len(docs)} city/event documents with embeddings.")
    print(json.dumps({"sample": docs[0]["name"], "dim": len(docs[0]["embedding"])}))


if __name__ == "__main__":  # pragma: no cover
    main()
