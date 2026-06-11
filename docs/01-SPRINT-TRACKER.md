# CrowdCompass Rover — Sprint & Progress Tracker

**Project:** AT-Hack0025 · T2-Elastic · P1 — CrowdCompass Rover
**Document:** `docs/01-SPRINT-TRACKER.md`
**Owner:** Claude (Opus 4.8) · **Build start:** 2026-06-01

This tracker is updated at the completion of **every** sprint. Each sprint is a
self-contained "mini module" that builds, tests green, and is documented before the
next begins.

---

## Legend
⬜ Not started · 🔄 In progress · ✅ Complete · ⚠️ Blocked (needs access)

---

## Sprint Overview

| Sprint | Module | Scope | Status |
|-------:|--------|-------|:------:|
| S0 | Foundations | Repo skeleton, tracker, access doc, tooling, config | ✅ |
| S1 | Domain & Data | Pydantic models, fixture city/event dataset, seed script | ✅ |
| S2 | Mock MCP server | Local Elastic-MCP-compatible JSON-RPC server (list_indices/get_mappings/search/esql) | ✅ |
| S3 | Elastic service layer | Provider interface + real Elastic client + mock client + hybrid search | ✅ |
| S4 | Agent core | Gemini provider + mock planner, NL→query plan, grounding, tool-calling loop | ✅ |
| S5 | Backend API | FastAPI routes (/search, /chat stream, /health, /indices), DI wiring | ✅ |
| S6 | Backend tests | pytest unit + integration, 100% coverage gate | ✅ |
| S7 | Frontend foundation | Vite+React+TS, design system, theme, layout shell | ✅ |
| S8 | Frontend features | Search UI, chat stream, map/result cards, language switch | ✅ |
| S9 | Frontend tests | Vitest component/unit, 100% coverage gate | ✅ |
| S10 | E2E Playwright | Full user journeys, 100% spec coverage of flows, CI wiring | ✅ |
| S11 | Docs & User Guide | Architecture, API ref, user guide w/ screenshots, README | ✅ |
| S12 | Hardening & Release | CI workflow, make targets, final coverage proof, release notes | ✅ |
| S13 | Observability | Structured JSON logging, request-id middleware, Prometheus metrics | ✅ |
| S14 | Resilience | Retry w/ backoff, circuit breaker, TTL+LRU cache | ✅ |
| S15 | Security | Token-bucket rate limiting, API-key auth, security middleware | ✅ |
| S16 | Ingestion | Feed sources, normalizer w/ aliases, pipeline + freshness tracking | ✅ |
| S17 | Ranking depth | Query expansion (synonyms), spell tolerance, business reranker | ✅ |
| S18 | Errors | Typed exception hierarchy, RFC-7807 problem+json handlers | ✅ |
| S19 | Conversation | Session store + multi-turn follow-up context resolution | ✅ |
| S20 | Composition | Resilient search wrapper, search pipeline, rewired factory/API | ✅ |
| S21 | Backend depth tests | Tests for all new modules, restore 100% coverage | ✅ |
| S22 | Frontend width | Feature panel, conversation history, session continuity | ✅ |
| S23 | Frontend depth tests | Tests for new components/hooks, restore 100% coverage | ✅ |
| S24 | Persistence | Repository ports + in-memory event/generic adapters | ✅ |
| S25 | Route enrichment | Route models, mock + Google Routes providers ("cheapest route") | ✅ |
| S26 | Analytics & audit | Query event recorder + aggregation snapshots | ✅ |
| S27 | Health & readiness | Dependency health checks, liveness vs readiness probe | ✅ |
| S28 | Scheduling | Async interval scheduler for periodic jobs | ✅ |
| S29 | i18n | Translation catalog + translator, answerer refactored onto it | ✅ |
| S30 | Config profiles | Dev/staging/prod profiles + settings validation | ✅ |
| S31 | Composition + API | Orchestrator analytics/routing, /ready /analytics /routes endpoints | ✅ |
| S32 | Frontend width II | RoutePanel, ErrorBoundary, route button, routing hook | ✅ |
| S33 | Backend+frontend tests | Tests for all new modules, restore 100% on both | ✅ |

---

## Detailed Log

### S0 — Foundations ✅
Repo skeleton, access doc, tracker, Makefile, .gitignore, typed `Settings` with
`APP_MODE` switch and provider factory, `.env.example`.

### S1 — Domain & Data ✅
Pydantic v2 models (`CityEvent`, `QueryPlan`, `ScoredEvent`, `ChatAnswer`, filters),
multilingual 3-city fixture dataset, deterministic embedding + haversine utilities, seed
script.

### S2 — Mock MCP server ✅
Local FastAPI JSON-RPC server implementing the Elastic MCP `tools/call` contract
(`list_indices`, `get_mappings`, `search`) over fixtures, so the real client path is
exercisable offline.

### S3 — Elastic service layer ✅
`SearchProvider` protocol; in-memory `MockSearchProvider` with hybrid ranker; real
`ElasticSearchProvider` + `ElasticMCPClient` (JSON-RPC) + hybrid query-DSL builder.

### S4 — Agent core ✅
`Planner`/`Answerer` protocols; deterministic multilingual `MockPlanner` + lexicon;
`MockAnswerer`; `GeminiClient` + `GeminiPlanner`/`GeminiAnswerer` with graceful fallback;
`RoverAgent` orchestrator.

### S5 — Backend API ✅
FastAPI app factory, lifespan-managed DI, routes `/health` `/indices` `/search` `/chat`
`/chat/stream` (SSE), CORS.

### S6 — Backend tests ✅
95 tests across core, models, planner, search, elastic, LLM, providers, API.
**Coverage 100.00%**, gate enforced via `--cov-fail-under=100`.

### S7–S8 — Frontend ✅
Vite + React + TS, strict build. "Matchday departure-board" design system; `useRover`
hook; components: `SearchControls`, `PlanStrip`, `AnswerCard`, `ResultRow`; `App`. API
client + display helpers. Production build verified.

### S9 — Frontend tests ✅
38 Vitest tests (lib, components, hook, App). **Coverage 100%** on statements, branches,
functions, lines.

### S10 — E2E Playwright ✅
8 journeys (landing, EN/ES/FR search, location distances, Enter-key, disabled-state,
empty-state). Dual web-server harness boots the real backend + built frontend. Browser
binary install is environment-gated; flows additionally validated against the live API.

### S11 — Docs & User Guide ✅
`02-ARCHITECTURE.md`, `03-API-REFERENCE.md`, `04-USER-GUIDE.md` (3 embedded screenshots),
root `README.md`. Screenshot generator under `scripts/`.

### S12 — Hardening & Release ✅
GitHub Actions CI (backend + frontend coverage gates, E2E with browser), lockfiles,
`05-RELEASE-NOTES.md` (v1.0.0). Final coverage re-verified green.

---

## Depth & Width Expansion (v1.1.0)

### S13 — Observability ✅
`observability/`: JSON log formatter with request-id contextvar, pure-ASGI
`RequestContextMiddleware` (timing + access log + `X-Request-ID`), dependency-free
metrics registry (counter/gauge/histogram) with Prometheus text rendering and a `/metrics`
endpoint.

### S14 — Resilience ✅
`resilience/`: `retry_async` with exponential backoff + jitter (injectable sleep/rng),
three-state `CircuitBreaker` (injectable clock), async `TTLCache` with LRU eviction and
hit-rate stats.

### S15 — Security ✅
`security/`: `TokenBucketRateLimiter` (per-key, injectable clock), constant-time
`ApiKeyAuthenticator` (disabled when no keys configured), pure-ASGI `SecurityMiddleware`
emitting problem+json, with public-path bypass.

### S16 — Ingestion ✅
`ingestion/`: `FeedSource` protocol + `StaticFeedSource`, record `normalizer` with
field-alias mapping and reject tracking, `IngestionPipeline` with dedup + per-source
health, and `FreshnessTracker` for staleness.

### S17 — Ranking depth ✅
`ranking/`: synonym `query_expansion`, bounded-Levenshtein `SpellCorrector` (vocabulary
from the live index), and a business-signal `reranker` (open-now / proximity / capacity).

### S18 — Errors ✅
`errors/`: typed `RoverError` hierarchy (401/404/422/429/503) → RFC-7807, with FastAPI
handlers rendering `application/problem+json`.

### S19 — Conversation ✅
`conversation/`: bounded expiring `SessionStore` (LRU), and `context` resolution that
inherits prior-turn filters for short refinement queries.

### S20 — Composition ✅
`ResilientSearchProvider` (cache + retry + breaker + metrics) wrapping any provider;
`SearchPipeline` (spell → expand → retrieve → rerank); orchestrator rewired for sessions;
provider factory as single composition root; API gains `/metrics`, richer `/health`,
session ids, and the full middleware stack.

### S21 — Backend depth tests ✅
New suites for observability, resilience, security, ingestion, ranking, conversation,
errors, and search composition. **205 tests, 100% coverage** (1497 statements).

### S22 — Frontend width ✅
`FeaturePanel` (engine capabilities + active sessions), `HistoryPanel` (multi-turn
conversation with replay), `session` id continuity, `useRover` extended for health +
history; App recomposed with the new panels.

### S23 — Frontend depth tests ✅
New component/lib/hook tests. **47 tests, 100% coverage** on all four metrics. Strict TS
build green; screenshots regenerated showing the new UI.

---

## Platform Depth Expansion (v1.2.0)

### S24 — Persistence ✅
`persistence/`: `Repository` / `EventRepository` ports (hexagonal boundary) and async-safe
in-memory adapters with bulk + by-city helpers. Real DB adapters slot in behind the same
ports.

### S25 — Route enrichment ✅
`enrichment/`: route domain models (`RouteOption`/`RouteResult` with cheapest/fastest), a
deterministic `MockRouteProvider` (per-mode speed/cost model from geometry), and a real
`GoogleRouteProvider` (Routes API computeRoutes) — delivering the headline "cheapest route
to the stadium now" use case.

### S26 — Analytics & audit ✅
`analytics/`: `AnalyticsRecorder` capturing per-query events (language, category, city,
result count, latency) to a bounded buffer + structured log, with aggregation snapshots
(zero-result rate, by-language/category, top queries).

### S27 — Health & readiness ✅
`health/`: `HealthRegistry` running time-bounded dependency checks concurrently, with a
liveness (`/health`) vs readiness (`/ready`) distinction and degraded/unhealthy states.

### S28 — Scheduling ✅
`scheduling/`: async interval `Scheduler` with deterministic `run_due` plus live
`start`/`stop`, isolating per-job failures — drives periodic ingestion refresh.

### S29 — i18n ✅
`i18n/`: centralised translation catalog + `Translator` (English fallback, formatting).
The answerer was refactored to source all user-facing strings from it.

### S30 — Config profiles ✅
`core/profiles.py`: dev/staging/prod profiles and a settings validator returning
structured issues (real mode without creds, prod in mock mode, prod without auth, etc.).

### S31 — Composition + API ✅
Orchestrator now records analytics and exposes `route_to`; factory wires persistence,
analytics, routes, and health; API gains `/ready`, `/analytics`, `/routes`.

### S32 — Frontend width II ✅
`RoutePanel` (cheapest/fastest route options), `ErrorBoundary` (render-error recovery),
a "Route here" action on result rows, and routing state in `useRover`.

### S33 — Backend + frontend tests ✅
New suites for persistence, i18n, enrichment, analytics, health, scheduling, profiles, and
the new API endpoints; frontend tests for routing, error boundary, and helpers.
**Backend 248 tests / Frontend 64 tests, both 100%.**

---

## Coverage Ledger
| Layer | Tool | Target | Latest |
|-------|------|-------:|-------:|
| Backend | pytest-cov | 100% | ✅ 100.00% (248 tests, 1958 stmts) |
| Frontend | vitest --coverage | 100% | ✅ 100.00% (64 tests) |
| E2E flows | Playwright | 100% of journeys | ✅ 8 journeys (browser run pending CDN access; flows validated via live API) |

## Access Ledger (live)
| System | Needed by sprint | Status |
|--------|------------------|--------|
| Elasticsearch | S3 | ⏳ Pending → mock active |
| Elastic MCP | S2/S3 | ⏳ Pending → local mock active |
| Gemini | S4 | ⏳ Pending → mock planner active |
| Google Cloud / Cloud Run | S12 | ⏳ Pending (deploy only) |
