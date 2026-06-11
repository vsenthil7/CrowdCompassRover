# CrowdCompass Rover — Release Notes

**Document:** `docs/05-RELEASE-NOTES.md`

---

## v1.0.0 — 2026-06-01

First complete build of CrowdCompass Rover for AT-Hack0025 (T2 — Elastic, P1).

### Features
- **Agentic pipeline:** plan → hybrid search → grounded answer, coordinated by
  `RoverAgent`.
- **Hybrid retrieval:** BM25-style keyword score fused 50/50 with dense-vector cosine
  similarity, plus category / open-now / dietary / accessibility / `geo_distance` filters.
- **Multilingual:** automatic language detection and normalisation; answers in English,
  Spanish, French, Portuguese, German, and Arabic, with English fallback.
- **Elastic MCP integration:** real JSON-RPC client for `list_indices`, `get_mappings`,
  `search`, and `esql`, with a hybrid query-DSL builder; plus a local mock MCP server for
  pre-credential testing.
- **Gemini integration:** LLM-backed planner and answerer with deterministic fallbacks.
- **API:** `/search`, `/chat`, `/chat/stream` (SSE), `/health`, `/indices`.
- **Frontend:** React "matchday departure-board" UI — search controls, plan transparency
  strip, concierge answer card, ranked result board, location toggle, language switch.

### Quality
- Backend: **95 tests, 100% coverage** (statements/branches), gate enforced in CI.
- Frontend: **38 tests, 100% coverage** on statements, branches, functions, and lines.
- E2E: **8 Playwright journeys** across landing, multilingual search, location, keyboard,
  and empty-state flows; dual web-server (backend + built frontend) harness.
- Strict TypeScript build; deterministic, offline-capable test suite.

### Operating modes
- `APP_MODE=mock` (default) — fully offline deterministic data; used in CI.
- `APP_MODE=real` — live Elastic MCP + Gemini (requires credentials).
- `APP_MODE=hybrid` — real Elastic, deterministic LLM (or partial combinations).

### Known limitations / follow-ups
- Localized answer templates cover six languages; others fall back to English.
- The deterministic mock embedding is a stable hashing projection for offline parity, not
  a semantic model; real mode uses Elastic/Gemini vectors.
- Playwright's browser binary must be installed where outbound access to the browser CDN
  is permitted (`npx playwright install chromium`); CI does this with `--with-deps`.
- Google Maps Routes enrichment ("cheapest route") is stubbed pending an API key.

### Upgrade / deploy notes
- Backend deploys to Cloud Run; frontend builds to static assets behind the same origin
  (the `/api` proxy in dev/preview mirrors the production same-origin setup).
- No secrets are committed; configure via `backend/.env` from `.env.example`.
