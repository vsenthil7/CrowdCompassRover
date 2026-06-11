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

- **One agent, three stages:** plan → hybrid search → grounded answer.
- **Production concerns built in:** structured logging + Prometheus metrics, retry /
  circuit-breaker / caching resilience, rate limiting + API-key auth, RFC-7807 errors,
  an ingestion pipeline with freshness tracking, and multi-turn conversation sessions.
- **Ranking depth:** synonym query expansion, spell tolerance, and business-signal
  reranking (open-now / proximity / capacity) on top of hybrid keyword+vector+geo search.
- **Real + mock parity:** every integration (Elastic MCP, Gemini) has real code behind a
  provider interface, switched by a single `APP_MODE` env var — no code change to go live.
- **Multilingual:** English, Spanish, French, Portuguese, German, Arabic answer support;
  any-language input.
- **Quality bar:** backend **100%** test coverage (205 tests), frontend **100%** coverage
  (47 tests), Playwright E2E journeys, strict TypeScript.
- **Distinctive UI:** a "matchday departure-board" React interface with an engine-feature
  panel and conversation history.

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
│   │   ├── ingestion/     feed sources, normalizer, pipeline + freshness
│   │   ├── conversation/  session store + multi-turn context
│   │   ├── resilience/    retry, circuit breaker, TTL+LRU cache
│   │   ├── observability/ JSON logging, metrics, request middleware
│   │   ├── security/      rate limiting, API-key auth, middleware
│   │   ├── errors/        typed exceptions + problem+json handlers
│   │   ├── mcp/           Elastic MCP client + local mock MCP server
│   │   ├── core/          config, embedding, geo, provider factory
│   │   ├── models/        domain models
│   │   ├── data/          fixtures + seed
│   │   └── api/           routes + DI
│   └── tests/          205 tests @ 100% coverage
├── frontend/           Vite + React + TS UI
│   ├── src/            components (incl. FeaturePanel, HistoryPanel), hooks, lib, styles
│   └── tests/          47 tests @ 100% coverage
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
