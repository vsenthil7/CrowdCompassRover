"""P2.S4 (Gemini side) — live answer generation via the real generateContent endpoint."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


async def test_gemini_generates_text(gemini_env):
    """The live Gemini client returns a non-empty answer for a grounded prompt."""
    from app.agent.gemini_client import GeminiClient  # real client, live key

    client = GeminiClient(gemini_env["GEMINI_API_KEY"])
    try:
        text = await client.generate_text(
            "You are a concierge. Answer briefly in English.",
            "Where can I find halal food near the stadium? Context: Halal Grill, Doha.",
        )
        assert isinstance(text, str)
        assert text.strip() != ""
    finally:
        await client.aclose()
