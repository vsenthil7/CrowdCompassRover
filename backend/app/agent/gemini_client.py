"""Thin async client for the Gemini generateContent API (REAL mode).

Kept dependency-light (httpx only). Used by GeminiPlanner and GeminiAnswerer. Covered by
unit tests through a stubbed transport so request/response handling is fully tested even
without a live key.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(RuntimeError):
    """Raised on a Gemini API error response."""


class GeminiClient:
    """Minimal Gemini generateContent client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=_BASE, timeout=timeout, transport=transport
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def generate_json(self, system: str, user: str) -> Any:
        """Generate a response and parse it as JSON.

        The prompt instructs the model to return strict JSON; we strip code fences
        defensively before parsing.
        """
        text = await self.generate_text(system, user)
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)

    async def generate_text(self, system: str, user: str) -> str:
        """Generate a plain-text response."""
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        }
        resp = await self._client.post(
            f"/models/{self._model}:generateContent",
            params={"key": self._api_key},
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise GeminiError(str(data["error"]))
        candidates = data.get("candidates", [])
        if not candidates:
            raise GeminiError("no candidates returned")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
