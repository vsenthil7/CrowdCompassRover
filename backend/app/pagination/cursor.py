"""Cursor-based pagination utilities.

Encodes an opaque, tamper-evident cursor (base64 of offset + a checksum) so clients page
through result sets without leaking internal indexing or trusting client-supplied offsets
blindly. Provides a generic paginator over any in-memory sequence; the same cursor scheme
maps onto Elasticsearch ``search_after`` in real mode.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

T = TypeVar("T")

_SECRET = b"crowdcompass-cursor-v1"


class InvalidCursorError(ValueError):
    """Raised when a cursor is malformed or fails its checksum."""


def _checksum(offset: int) -> str:
    return hashlib.sha256(f"{offset}".encode() + _SECRET).hexdigest()[:8]


def encode_cursor(offset: int) -> str:
    """Encode an offset into an opaque cursor string."""
    payload = {"o": offset, "c": _checksum(offset)}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> int:
    """Decode and verify a cursor, returning the offset."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        payload = json.loads(raw)
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorError("malformed cursor") from exc
    offset = payload.get("o")
    checksum = payload.get("c")
    if not isinstance(offset, int) or checksum != _checksum(offset):
        raise InvalidCursorError("cursor failed verification")
    return offset


@dataclass
class Page(Generic[T]):
    """A page of items plus the cursor to fetch the next page."""

    items: list[T]
    next_cursor: str | None
    total: int

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None


def paginate(items: Sequence[T], *, cursor: str | None, limit: int) -> Page[T]:
    """Return a page of ``items`` starting at ``cursor`` with up to ``limit`` entries."""
    if limit < 1:
        raise ValueError("limit must be >= 1")
    offset = decode_cursor(cursor) if cursor else 0
    if offset < 0 or offset > len(items):
        raise InvalidCursorError("cursor out of range")
    window = list(items[offset : offset + limit])
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < len(items) else None
    return Page(items=window, next_cursor=next_cursor, total=len(items))
