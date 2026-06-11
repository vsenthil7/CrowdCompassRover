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

---

## v1.1.0 — 2026-06-01

Enterprise depth & width expansion. Backend grew from ~1.7k to ~3.4k lines across 59
modules; tests from 95 → 205; frontend tests from 38 → 47. All at 100% coverage.

### New backend capabilities
- **Observability** — structured JSON logging with request-id correlation, a
  dependency-free Prometheus metrics registry, and a `/metrics` endpoint; request-timing
  and access logging middleware.
- **Resilience** — exponential-backoff retry, a three-state circuit breaker, and a
  TTL+LRU cache, composed into a `ResilientSearchProvider` wrapper around any backend.
- **Security** — token-bucket rate limiting and API-key authentication via pure-ASGI
  middleware, with problem+json rejections and public-path bypass.
- **Ingestion pipeline** — pluggable feed sources, a field-alias-aware normalizer with
  reject tracking, dedup + per-source health, and freshness/staleness tracking.
- **Ranking depth** — synonym query expansion, bounded-Levenshtein spell tolerance, and a
  business-signal reranker (open-now / proximity / capacity), composed in a `SearchPipeline`.
- **Errors** — typed exception hierarchy mapped to RFC-7807 `application/problem+json`.
- **Conversation** — expiring session store and multi-turn follow-up context resolution
  (a short "what about open ones?" inherits the prior turn's city/category filters).

### New frontend capabilities
- **FeaturePanel** surfacing active engine capabilities and live session count.
- **HistoryPanel** showing the multi-turn conversation with one-tap replay.
- Session-id continuity so the backend threads context across queries.

### API additions
- `GET /api/metrics` (Prometheus text format).
- `GET /api/health` now reports active sessions and enabled features.
- `/search` and `/chat` accept an optional `session_id`.
- Full middleware stack: request-context → security → CORS.

### Config additions
- Security: `API_KEYS`, `RATE_LIMIT_RATE`, `RATE_LIMIT_CAPACITY`.
- Resilience: `RETRY_MAX_ATTEMPTS`, `CIRCUIT_FAIL_MAX`, `CIRCUIT_RESET_TIMEOUT`,
  `CACHE_TTL`, `CACHE_MAXSIZE`.
- Ranking toggles: `ENABLE_RERANKING`, `ENABLE_QUERY_EXPANSION`, `ENABLE_SPELL_CORRECTION`.
- Conversation: `SESSION_TTL`. Observability: `LOG_LEVEL`. Ingestion: `INGEST_STALE_AFTER`.
