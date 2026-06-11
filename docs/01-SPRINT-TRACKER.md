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
| S34 | Tracing | OpenTelemetry-style nested spans + exporter | ✅ |
| S35 | Event bus | Async pub/sub with typed domain events | ✅ |
| S36 | Feature flags | Runtime flags with rollout % + targeting | ✅ |
| S37 | Input hardening | Sanitisation, injection neutralisation, abuse guards | ✅ |
| S38 | Pagination | Tamper-evident cursor + generic paginator | ✅ |
| S39 | Batch API | Multi-query submission | ✅ |
| S40 | Concurrency + saved | Versioned repo (optimistic locking) + saved searches | ✅ |
| S41 | Admin/ops surface | Cache flush, reindex, status, flag inspect | ✅ |
| S42 | Composition + API | Orchestrator tracing/events/pagination/sanitise, 11 new endpoints | ✅ |
| S43 | Frontend width III | Pagination, SavedSearches; tests to 100% on both | ✅ |
| S44 | Authz / RBAC | Roles, permissions, principal resolver, policy engine | ✅ |
| S45 | Audit log | Hash-chained, tamper-evident append-only log | ✅ |
| S46 | Webhooks | Subscriber registry + HMAC-signed retried delivery | ✅ |
| S47 | Idempotency | Idempotency-key store + idempotent reindex | ✅ |
| S48 | Usage metering | Per-tenant monthly quotas + accounting | ✅ |
| S49 | GDPR | Data export + purge for a subject | ✅ |
| S50 | Notifications | Alert rules, severities, cooldown, channels | ✅ |
| S51 | Composition + API | Wire all into factory; 6 new endpoints | ✅ |
| S52 | Backend tests | Tests for all new modules; restore 100% | ✅ |
| S53 | Frontend a11y + client | a11y helpers module, admin/usage/audit API client | ✅ |
| S54 | Admin dashboard | AdminDashboard, UsageView, useAdmin hook | ✅ |
| S55 | Frontend tests | Tests for new components/hook; restore 100% on both | ✅ |
| S56 | Tenancy | Tenant context, validation, allow-list resolver | ✅ |
| S57 | API versioning | Version registry + deprecation/sunset headers | ✅ |
| S58 | Outbox | Transactional outbox, relay, retry, dead-letter | ✅ |
| S59 | Secrets | Provider abstraction + rotation overlap window | ✅ |
| S60 | Concurrency | Bulkhead limiter with bounded queue | ✅ |
| S61 | Retention | TTL sweeper for analytics + audit | ✅ |
| S62 | SLO | Error-budget + SLO computation from outcomes | ✅ |
| S63 | Composition + API | Wire all into factory; 6 new endpoints | ✅ |
| S64 | Backend tests | Tests for all new modules; restore 100% | ✅ |
| S65 | Frontend client | SLO/version types + API client methods | ✅ |
| S66 | SLO + version UI | SloPanel, VersionBadge, dashboard wiring | ✅ |
| S67 | Frontend tests | Tests for new components/hook; restore 100% on both | ✅ |
| S68 | Wiring: outbox bridge | Event bus → outbox → webhook relay made load-bearing | ✅ |
| S69 | Wiring: bulkhead + SLO | Bulkhead fronts search/chat; SLO records failures | ✅ |
| S70 | Tenant scoped store | Structural per-tenant data partitioning | ✅ |
| S71 | Frontend outbox panel | OutboxPanel + relay action; integration tests; 100% | ✅ |
| S72 | Operator observability UI | Surface analytics/traces/flags/readiness/bulkhead/retention into the ops dashboard | ✅ |

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

## Production Hardening Expansion (v1.3.0)

### S34 — Tracing ✅
`tracing/`: OpenTelemetry-style `Tracer`/`Span` with context-var propagation, nested
parent/child spans, error status capture, and a bounded `SpanExporter`. Spans recorded
across plan → retrieve → ground.

### S35 — Event bus ✅
`events/`: async `EventBus` with typed `DomainEvent`s (`SearchPerformed`, `ZeroResult`,
`RouteRequested`); handler failures isolated; default zero-result → metrics handler wired.

### S36 — Feature flags ✅
`flags/`: `FeatureFlag`/`FeatureFlags` with stable percentage-rollout bucketing (hash of
flag+subject) and allow/deny targeting; runtime `refresh`.

### S37 — Input hardening ✅
`security/sanitize.py`: NFKC normalisation, control-char stripping, whitespace collapse,
injection-marker neutralisation, length/token caps, and repetition abuse flagging.

### S38 — Pagination ✅
`pagination/`: tamper-evident base64 cursor (offset + checksum) and a generic `paginate`
over any sequence; maps onto ES `search_after` in real mode.

### S39 — Batch API ✅
Orchestrator `batch_search` + `/search/batch` endpoint for multi-query submission.

### S40 — Concurrency + saved searches ✅
`persistence/versioned.py`: versioned repository with optimistic-locking
`ConcurrencyError`. `persistence/saved_search.py`: owner-scoped saved searches over it.

### S41 — Admin/ops surface ✅
`admin/`: `AdminService` for cache flush, reindex (re-run ingestion → event repo),
status summary, and flag inspection.

### S42 — Composition + API ✅
Orchestrator now traces every stage, sanitises input, publishes domain events, and
paginates; factory wires tracer, bus, flags, saved searches, ingestion, admin. Added
`/ready` `/analytics` `/routes` `/search/batch` `/saved-searches` (CRUD) `/flags`
`/traces` `/admin/*` endpoints. Fixed normalizer nested-location handling and pagination
candidate windowing.

### S43 — Frontend width III ✅
`Pagination` (load-more with total/end states) and `SavedSearches` (save/run/delete);
`useRover` extended with pagination accumulation and saved-search CRUD. **Backend 313
tests / Frontend 90 tests, both 100%.** Strict TS build green.

---

## Enterprise Governance Expansion (v1.4.0)

### S44 — Authz / RBAC ✅
`authz/`: `Permission` enum, `Role` (frozen permission sets), `Principal`, built-in
visitor/analyst/admin hierarchy, a `PrincipalResolver` (API key → principal) and a
`PolicyEngine` raising a typed 403 `AuthorizationError`.

### S45 — Audit log ✅
`audit/`: append-only, hash-chained `AuditLog` (each entry's hash includes the previous),
`verify()` detecting any tampering, plus actor/tenant filtering.

### S46 — Webhooks ✅
`webhooks/`: `WebhookRegistry` + `WebhookDispatcher` delivering HMAC-SHA256-signed payloads
to external subscribers with bounded retries, via an injected sender (testable offline).

### S47 — Idempotency ✅
`idempotency/`: `IdempotencyStore` (NEW/IN_FLIGHT/COMPLETED states, TTL expiry); the admin
reindex endpoint honours an `Idempotency-Key` header and replays the prior result.

### S48 — Usage metering ✅
`metering/`: per-tenant monthly `UsageMeter` with quota enforcement (typed 429
`QuotaExceededError`), period rollover, and per-action accounting.

### S49 — GDPR ✅
`gdpr/`: `DataRightsService` exporting a subject's sessions, saved searches, and audit
entries into one document, and purging them — using clean public APIs on the collaborators
(added `SavedSearchService.list_by_owner`, `VersionedRepository.list_values`,
`SessionStore.drop`).

### S50 — Notifications ✅
`notifications/`: `AlertManager` evaluating rules over a snapshot, with severities, cooldown
suppression, and pluggable channels (built-in structured-log channel).

### S51 — Composition + API ✅
Factory wires resolver, policy, audit, webhooks, idempotency, meter, data-rights, and a
default alert manager (high zero-result rate; dependency unhealthy). New endpoints:
`/audit`, `/webhooks` (create/delete), `/usage/{tenant}`, `/gdpr/export/{subject}`,
`/gdpr/{subject}` (purge); reindex made idempotent.

### S52 — Backend tests ✅
New suites for authz, audit, idempotency, webhooks, metering, GDPR, alerts, the new factory
builders, and the new endpoints. Caught and fixed a logging-capture flake. **Backend 371
tests, 100%.**

### S53 — Frontend a11y + client ✅
`lib/a11y.ts` (keyboard-activation, aria-live, age/percent formatters) and admin/usage/audit
methods on the API client.

### S54 — Admin dashboard ✅
`AdminDashboard`, `UsageView`, and the `useAdmin` hook (status/usage/audit load, reindex,
flush cache); an accessible "Ops" toggle in the masthead.

### S55 — Frontend tests ✅
Tests for a11y helpers, the admin/usage components, the `useAdmin` hook, the new client
methods, and the App ops-toggle flow. **Backend 371 / Frontend 115 tests, both 100%.**

---

## Scale & Reliability Expansion (v1.5.0)

### S56 — Tenancy ✅
`tenancy/`: `TenantContext` (contextvar-propagated), id validation/normalisation, and a
`TenantResolver` (principal → header → default) with an optional allow-list and typed
400 errors for invalid/unknown tenants.

### S57 — API versioning ✅
`versioning/`: `VersionRegistry` tracking supported versions, the current one, and
deprecation/sunset advisory headers; default registry seeds `v1`.

### S58 — Outbox ✅
`outbox/`: transactional `Outbox` with `enqueue`, a `relay` that drains pending messages to
a sink with retries, `PENDING/DELIVERED/FAILED/DEAD` states, and dead-letter inspection —
closing the "event lost after commit" gap.

### S59 — Secrets ✅
`secrets/`: `SecretProvider` protocol + `EnvSecretProvider`, plus `RotatingSecret` accepting
the previous value during a configurable overlap window so rotation doesn't break in-flight
clients.

### S60 — Concurrency ✅
`concurrency/`: `Bulkhead` capping simultaneous in-flight work with a bounded wait queue and
fast `BulkheadFullError` (503) when saturated; counters survive cancellation.

### S61 — Retention ✅
`retention/`: policy-driven `RetentionSweeper` pruning records older than a max age.
Analytics and the audit log gained `prune_before`; audit `verify()` was made robust to a
pruned prefix so retention isn't mistaken for tampering.

### S62 — SLO ✅
`slo/`: `SloTracker` recording success/failure outcomes over a rolling window and computing
success ratio, error budget, and budget-remaining per service; the orchestrator records
search/chat outcomes.

### S63 — Composition + API ✅
Factory wires tenants, versions, outbox, secrets, bulkhead, retention, and SLO; the agent
records SLO outcomes. New endpoints: `/slo`, `/version` (public), `/admin/outbox`,
`/admin/bulkhead`, `/admin/retention/sweep`; `/usage/{tenant}` now validates the tenant.

### S64 — Backend tests ✅
New suites for tenancy, versioning, outbox, secrets, bulkhead, retention, SLO, the new
factory builders, and endpoints; covered the bulkhead queue-cancellation branch. **Backend
422 tests, 100%.**

### S65 — Frontend client ✅
SLO/version types and `sloReport`/`versionInfo` API client methods; `useAdmin` extended to
load both.

### S66 — SLO + version UI ✅
`SloPanel` (per-service budget bars with ok/warning/critical states) and `VersionBadge`,
wired into the admin dashboard.

### S67 — Frontend tests ✅
Tests for `SloPanel`, `VersionBadge`, the extended `useAdmin`, the new client methods, and
the dashboard rendering. **Backend 422 / Frontend 124 tests, both 100%.**

---

## Wiring & Integration Hardening (v1.6.0)

> A self-review found three previously-built modules were present and unit-tested but **not
> actually load-bearing** in the request path. This round makes them real and proves it with
> end-to-end integration tests, rather than adding new surface.

### S68 — Outbox bridge (made load-bearing) ✅
`events/outbox_bridge.py`: `OutboxBridge` subscribes to the event bus and durably enqueues
published domain events into the outbox; `WebhookOutboxSink` drains the outbox to signed
webhook subscribers with retry/dead-lettering. Previously the outbox was never written to.
New `/admin/outbox/relay` endpoint drives the relay. Verified end to end: search → 1
pending → relay → 1 delivered.

### S69 — Bulkhead + SLO (made load-bearing) ✅
The orchestrator now runs every search/chat retrieval through the bulkhead
(`_run_pipeline`), proven by a test where a saturated bulkhead makes search raise
`BulkheadFullError`. The SLO tracker now records **failures** as well as successes (it was
success-only, hence meaningless before).

### S70 — Tenant scoped store ✅
`tenancy/scoped_store.py`: `TenantScopedStore` enforces per-tenant partitioning structurally
(outer key = tenant), with isolation tests proving no cross-tenant reads — turning tenancy
from advisory into enforced.

### S71 — Frontend outbox panel ✅
`OutboxPanel` (pending/delivered/failed/dead counts, dead-letter list, "Relay now" action)
wired into the admin dashboard; `useAdmin` gained outbox state + `relayOutbox`. Added
integration tests for the bridge, sink, scoped store, and wired orchestrator behaviour.
**Backend 436 / Frontend 130 tests, both 100%.**

### S72 — Operator observability UI ✅
**Gap found:** the backend exposed 30 endpoints but the frontend surfaced only ~13 — a
cluster of built, tested, but UI-invisible capabilities (the same "exists but not
load-bearing in the UI" pattern hardened against in S68–S71). This sprint surfaced the
remaining operator-facing depth into the ops dashboard.

- **API client + types:** `analytics`, `traces`, `flags`, `readiness`, `bulkheadStats`,
  `sweepRetention` (typed against the real endpoint shapes; `/ready` reads its body on both
  200 and 503).
- **Five modular panels:** `AnalyticsPanel` (volume, zero-result rate, language/category
  breakdowns, top queries), `TracesPanel` (recent spans, parent-indented, cycle-guarded),
  `FlagsPanel` (evaluated feature flags), `HealthPanel` (per-dependency readiness),
  `BulkheadPanel` (concurrency utilisation with saturation states).
- **Hook + dashboard:** `useAdmin` loads all five surfaces in its `refresh` fan-out and adds
  a `sweepRetention` action; `AdminDashboard` renders the new sections and a "Sweep
  retention" control.
- **Tests:** new `observability-panels.test.tsx` (all branches incl. empty states, each
  severity class, cyclic-trace guard), extended `lib.test.ts` (6 new client methods incl.
  the 503 readiness path) and `admin.test.tsx` (populated-dashboard render + sweep action +
  hook fan-out and error paths).

**Backend 436 / Frontend 156 tests, both 100%.** Backend untouched; production build clean.

---

## Coverage Ledger
| Layer | Tool | Target | Latest |
|-------|------|-------:|-------:|
| Backend | pytest-cov | 100% | ✅ 100.00% (436 tests, 3472 stmts) |
| Frontend | vitest --coverage | 100% | ✅ 100.00% (156 tests) |
| E2E flows | Playwright | 100% of journeys | ✅ 8 journeys (browser run pending CDN access; flows validated via live API) |

## Access Ledger (live)
| System | Needed by sprint | Status |
|--------|------------------|--------|
| Elasticsearch | S3 | ⏳ Pending → mock active |
| Elastic MCP | S2/S3 | ⏳ Pending → local mock active |
| Gemini | S4 | ⏳ Pending → mock planner active |
| Google Cloud / Cloud Run | S12 | ⏳ Pending (deploy only) |
