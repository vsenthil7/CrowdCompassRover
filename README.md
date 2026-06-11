# CrowdCompass Rover

**Multilingual semantic-search agent for 2026 World Cup host cities.**
Google Cloud Rapid Agent Hackathon (AT-Hack0025) · Track T2 — Elastic · Product P1.

Ask, in any language, *"cheapest route to the stadium now"*, *"nearest open halal
restaurant"*, or *"where to exchange currency"* — Rover plans the query, runs a hybrid
keyword + vector + geo search over fast-changing city/event data, and replies with a
grounded, cited answer in your language.

Built **100% agentic** on the **Elastic MCP server** (hybrid search) and **Google Cloud
Agent Builder / Gemini** (multilingual reasoning).

---

## Highlights

- **One agent, three stages:** plan → hybrid search → grounded answer, plus route
  enrichment for the "cheapest route to the stadium now" use case.
- **Production concerns built in:** structured logging + Prometheus metrics, distributed
  tracing, an async event bus, a transactional outbox, runtime feature flags, retry /
  circuit-breaker / caching / bulkhead resilience, RBAC authorization, a tamper-evident
  audit log, signed webhook delivery, idempotency, multi-tenancy, per-tenant usage quotas,
  GDPR export/purge, data-retention sweeping, SLO / error-budget tracking, alerting, a
  secrets abstraction, API versioning, rate limiting + API-key auth + input sanitisation,
  RFC-7807 errors, an ingestion pipeline with freshness tracking, multi-turn sessions,
  query analytics, dependency health/readiness probes, a job scheduler, a persistence
  repository layer with optimistic concurrency, saved searches, pagination, a batch API, an
  admin/ops surface, i18n, and per-environment config validation.
- **Ranking depth:** synonym query expansion, spell tolerance, and business-signal
  reranking (open-now / proximity / capacity) on top of hybrid keyword+vector+geo search.
- **Real + mock parity:** every integration (Elastic MCP, Gemini, Google Routes) has real
  code behind a provider interface, switched by `APP_MODE` + credentials — no code change.
- **Multilingual:** English, Spanish, French, Portuguese, German, Arabic answer support.
- **Quality bar:** backend **100%** coverage (499 tests), frontend **100%** coverage
  (174 tests), Playwright E2E journeys, strict TypeScript. Domain events flow through a
  durable outbox to signed webhooks; search runs behind a concurrency bulkhead; SLOs track
  real error budgets — all covered by end-to-end integration tests.
- **Distinctive UI:** a "matchday departure-board" React interface with engine-feature
  panel, conversation history, route options, saved searches, pagination, and an accessible
  admin/ops dashboard (status, usage, SLO budgets, audit, API version) with an error
  boundary.

---

## Quickstart (mock mode — no credentials needed)

```bash
# 1. Install
make install

# 2. Run the backend (terminal 1)
make run-backend          # http://localhost:8000  (/docs for OpenAPI)

# 3. Run the frontend (terminal 2)
make run-frontend         # http://localhost:5173
```

Open http://localhost:5173 and ask a question. The mode badge will read **mock**.

### Run the tests

```bash
make test-backend         # pytest, 100% coverage gate
make test-frontend        # vitest, 100% coverage gate
make test-e2e             # Playwright (needs browser: npm --prefix e2e run install-browsers)
```

---

## Going live (real mode)

1. Provide credentials in `backend/.env` (template: `backend/.env.example`):
   Elasticsearch URL + API key, Elastic MCP endpoint + key, Gemini API key.
2. Set `APP_MODE=real`.
3. `make seed && make test-real`.

See **`docs/00-ACCESS-REQUIREMENTS.md`** for the full access matrix and what each grant
unlocks. Until provided, the corresponding subsystem runs deterministically in mock mode.

A local **mock Elastic MCP server** (`make run-mcp`) lets you exercise the *real* MCP
client/provider path before live Elastic access is available.

---

## Documentation

| Doc | Contents |
|-----|----------|
| `docs/00-ACCESS-REQUIREMENTS.md` | Credentials/access matrix, mock↔real switching |
| `docs/01-SPRINT-TRACKER.md` | Sprint-by-sprint build log and coverage ledger |
| `docs/02-ARCHITECTURE.md` | System design, request lifecycle, module map |
| `docs/03-API-REFERENCE.md` | Endpoint reference incl. SSE streaming |
| `docs/04-USER-GUIDE.md` | End-user guide with screenshots |
| `docs/05-RELEASE-NOTES.md` | v1.0.0 release notes |

---

## Repository layout

```
crowdcompass-rover/
├── backend/            FastAPI + agent + Elastic/Gemini providers (Python 3.12)
│   ├── app/
│   │   ├── agent/         planner, answerer, Gemini client, orchestrator
│   │   ├── services/      hybrid ranker, mock + Elastic search, query builder,
│   │   │                  resilient wrapper, search pipeline
│   │   ├── ranking/       query expansion, spell tolerance, business reranker
│   │   ├── enrichment/    route models, mock + Google Routes providers
│   │   ├── persistence/   repository ports, in-memory + versioned adapters, saved searches
│   │   ├── authz/         RBAC roles, permissions, principal resolver, policy engine
│   │   ├── audit/         hash-chained tamper-evident audit log
│   │   ├── webhooks/      subscriber registry + signed retried delivery
│   │   ├── idempotency/   idempotency-key store
│   │   ├── metering/      per-tenant usage quotas
│   │   ├── gdpr/          data export + purge
│   │   ├── notifications/ alert rules, severities, channels
│   │   ├── tenancy/       tenant context, validation, resolver
│   │   ├── versioning/    API version registry + deprecation headers
│   │   ├── outbox/        transactional outbox (relay, retry, dead-letter)
│   │   ├── secrets/       secret provider abstraction + rotation
│   │   ├── concurrency/   bulkhead concurrency limiter
│   │   ├── retention/     policy-driven TTL sweeper
│   │   ├── slo/           SLO + error-budget tracking
│   │   ├── availability/  timezone-aware opening hours, evaluator, seed, service
│   │   ├── livesignals/   live crowd/wait/closure signals with freshness decay
│   │   ├── analytics/     query event recorder + aggregation
│   │   ├── tracing/       OpenTelemetry-style spans + exporter
│   │   ├── events/        async event bus + typed domain events
│   │   ├── flags/         runtime feature flags (rollout % + targeting)
│   │   ├── pagination/    cursor encoding + paginator
│   │   ├── admin/         ops surface (cache flush, reindex, status)
│   │   ├── health/        dependency health checks (liveness/readiness)
│   │   ├── scheduling/    async interval scheduler
│   │   ├── i18n/          translation catalog + translator
│   │   ├── ingestion/     feed sources, normalizer, pipeline + freshness
│   │   ├── conversation/  session store + multi-turn context
│   │   ├── resilience/    retry, circuit breaker, TTL+LRU cache
│   │   ├── observability/ JSON logging, metrics, request middleware
│   │   ├── security/      rate limiting, API-key auth, sanitisation, middleware
│   │   ├── errors/        typed exceptions + problem+json handlers
│   │   ├── mcp/           Elastic MCP client + local mock MCP server
│   │   ├── core/          config, profiles, embedding, geo, provider factory
│   │   ├── models/        domain models
│   │   ├── data/          fixtures + seed
│   │   └── api/           routes + DI
│   └── tests/          499 tests @ 100% coverage
├── frontend/           Vite + React + TS UI
│   ├── src/            components (Result/Plan/Answer/Feature/History/Route/Saved panels,
│   │                   Pagination, AdminDashboard, UsageView, SloPanel, OutboxPanel,
│   │                   Analytics/Traces/Flags/Health/Bulkhead panels, AvailabilityBadge,
│   │                   VersionBadge, ErrorBoundary), hooks, lib, styles
│   └── tests/          174 tests @ 100% coverage
├── e2e/                Playwright journeys + dual web-server config
├── docs/               architecture, API, user guide (+ screenshots), tracker
├── scripts/            screenshot snapshot generator
└── Makefile            developer entry points
```

---

## Tech stack

FastAPI · Pydantic v2 · httpx · sse-starlette · React 18 · Vite 5 · TypeScript ·
Vitest · Playwright · Elasticsearch (MCP) · Google Cloud Agent Builder / Gemini ·
Cloud Run.

## License

Prepared for AT-Hack0025. Internal hackathon deliverable.
