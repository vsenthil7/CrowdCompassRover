# CrowdCompass Rover — Architecture

**Document:** `docs/02-ARCHITECTURE.md` · **Updated:** 2026-06-01

CrowdCompass Rover is a multilingual semantic-search agent that answers fast-changing
"where / how / what now" questions for 2026 World Cup host-city visitors. It is built on
the **Elastic MCP server** (hybrid keyword + vector + geo search) and **Google Cloud
Agent Builder / Gemini** for multilingual reasoning, packaged as a fully agentic AI
product.

---

## 1. System at a glance

```
                ┌────────────────────────────────────────────────────────┐
                │                     Browser (React)                     │
                │   SearchControls · PlanStrip · AnswerCard · ResultRow   │
                └───────────────┬────────────────────────────────────────┘
                                │  POST /api/search · /api/chat · /chat/stream
                                ▼
                ┌────────────────────────────────────────────────────────┐
                │                  FastAPI backend (ASGI)                  │
                │                                                          │
                │   RoverAgent (orchestrator)                             │
                │     1. Planner    NL → QueryPlan (lang, filters)        │
                │     2. Search     hybrid retrieval over city/event data │
                │     3. Answerer   grounded, cited, language-matched      │
                └───────┬───────────────────────────┬─────────────────────┘
                        │                           │
          provider factory selects by APP_MODE      │
                        │                           │
        ┌───────────────┴───────┐        ┌──────────┴───────────┐
        ▼                       ▼        ▼                      ▼
  MockPlanner /            GeminiPlanner / MockSearchProvider   ElasticSearchProvider
  MockAnswerer             GeminiAnswerer  (in-memory hybrid)    → ElasticMCPClient
  (deterministic)          (Gemini API)                          → Elastic MCP server
                                                                    → Elasticsearch
```

Every integration sits behind a small interface. A single `APP_MODE` setting
(`mock` | `real` | `hybrid`) decides which concrete implementation the factory wires in,
so the same code runs offline in CI and against live services in production with no edits.

---

## 2. Request lifecycle

A user asks, in any language, e.g. *"dónde comer halal cerca ahora"*:

1. **Plan.** The planner detects the language, normalises the query to English, and
   extracts structured filters (city, category, open-now, dietary, proximity). In real
   mode Gemini does this; in mock mode a deterministic multilingual lexicon does, with the
   Gemini planner falling back to the lexicon on any error.
2. **Search.** The plan drives a **hybrid** query: a BM25-style keyword score fused 50/50
   with dense-vector cosine similarity, constrained by a filter context (category,
   open-now, halal/vegetarian/accessible, and `geo_distance` when a location is supplied).
   The mock provider computes this in-process; the real provider expresses the identical
   intent as an Elasticsearch query DSL + kNN body sent through the Elastic MCP `search`
   tool.
3. **Ground.** The answerer composes a concise, cited reply **in the user's language**,
   citing each place by name and reporting open/closed status and distance.

The contract between the three stages is the typed `QueryPlan` / `ScoredEvent` /
`ChatAnswer` models, so any stage can be swapped without disturbing the others.

---

## 3. Why these technologies

**Elastic** unifies keyword, vector, geo, and structured filtering in one engine with a
shipped MCP server — exactly what "open now + nearby + semantic, in any language" needs.
A vector-only store would force a second keyword/geo system and bespoke glue. The hybrid
fusion means a misspelled or non-English query still retrieves the right venue by meaning,
while structured filters keep "open now" and "within 5 km" exact.

**Google Cloud Agent Builder + Gemini** provide the multilingual reasoning that turns
free-text, code-switched questions into a precise plan, and Cloud Run autoscales for
bursty matchday load. Gemini's multilingual strength removes the need for a separate
translation service in the common case.

**Trade-offs.** Consumption-based Elastic cost rises with matchday spikes; relevance
tuning has a learning curve; and Gemini token cost and Google's own grounding can overlap
with Elastic. These are documented per-component in the idea brief and revisited in the
release notes.

---

## 4. Mock / real parity

The mock path is not a throwaway stub — it implements the same protocols, the same hybrid
scoring intent, and the same JSON-RPC contract as the Elastic MCP server (there is even a
local mock MCP server so the *real* client/provider code path can be exercised end-to-end
before live credentials arrive). This is what lets the test suite hold the whole pipeline
to 100% coverage offline while remaining a faithful rehearsal of production behaviour.

---

## 5. Module map

| Layer | Path | Responsibility |
|-------|------|----------------|
| Config | `app/core/config.py` | Typed settings, `APP_MODE`, mode predicates |
| Models | `app/models/domain.py` | `CityEvent`, `QueryPlan`, `ScoredEvent`, `ChatAnswer` |
| Data | `app/data/fixtures.py` | Multilingual host-city dataset |
| Embedding/Geo | `app/core/embedding.py`, `geo.py` | Deterministic vectors, haversine |
| Hybrid | `app/services/hybrid.py` | Keyword+vector+filter ranking |
| Search providers | `app/services/{mock_search,elastic_search}.py` | Mock + Elastic-MCP retrieval |
| Query DSL | `app/services/query_builder.py` | Plan → ES hybrid query body |
| MCP client | `app/mcp/elastic_client.py` | JSON-RPC to Elastic MCP server |
| Planner | `app/agent/{planner,gemini_planner}.py` | NL → plan (mock + Gemini) |
| Answerer | `app/agent/{answerer,gemini_planner}.py` | Grounded answer (mock + Gemini) |
| Orchestrator | `app/agent/orchestrator.py` | plan → search → ground |
| Factory | `app/core/providers.py` | Mode-driven dependency wiring |
| API | `app/api/routes.py`, `app/main.py` | HTTP + SSE endpoints, `/metrics` |
| Frontend | `frontend/src/**` | React UI (controls, board, answer, panels) |

### Cross-cutting modules (v1.1.0)

| Concern | Path | Responsibility |
|---------|------|----------------|
| Observability | `app/observability/` | JSON logging, metrics registry, request middleware |
| Resilience | `app/resilience/` | retry, circuit breaker, TTL+LRU cache |
| Security | `app/security/` | rate limiting, API-key auth, middleware |
| Ingestion | `app/ingestion/` | feed sources, normalizer, pipeline, freshness |
| Ranking | `app/ranking/` | query expansion, spell tolerance, reranker |
| Errors | `app/errors/` | typed exceptions, problem+json handlers |
| Conversation | `app/conversation/` | session store, multi-turn context |
| Composition | `app/services/resilient_search.py`, `search_pipeline.py` | resilient wrapper + ranking pipeline |
