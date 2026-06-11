# CrowdCompass Rover — API Reference

**Document:** `docs/03-API-REFERENCE.md` · **Base path:** `/api` · **Updated:** 2026-06-01

All endpoints accept and return JSON unless noted. The interactive OpenAPI UI is available
at `/docs` when the backend is running.

---

## GET `/api/health`

Liveness probe and active-mode report.

**200 response**
```json
{ "status": "ok", "mode": "mock" }
```
`mode` is one of `mock`, `real`, `hybrid`.

---

## GET `/api/indices`

Lists searchable indices via the active search provider (Elastic MCP `list_indices` in
real mode; the fixture index in mock mode).

**200 response**
```json
{ "indices": ["cc-city-events"] }
```

---

## POST `/api/search`

Runs a hybrid multilingual search and returns ranked results plus the plan that produced
them.

**Request body**
```json
{
  "query": "dónde comer halal cerca ahora",
  "user_location": { "lat": 19.30, "lon": -99.15 },
  "top_k": 5
}
```

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `query` | string (1–2000) | yes | Natural language, any supported language |
| `user_location` | `{lat, lon}` | no | Enables proximity filtering + distances |
| `top_k` | int (1–50) | no | Default 5 |

**200 response (abridged)**
```json
{
  "plan": {
    "detected_language": "es",
    "normalized_query": "where eat halal near now",
    "filters": { "halal": true, "open_now": true, "max_distance_km": 25.0 },
    "top_k": 5
  },
  "results": [
    {
      "event": { "id": "mex-taqueria-halal", "name": "Taquería Halal El Árabe",
                 "category": "restaurant", "city": "Mexico City", "open_now": true,
                 "halal": true },
      "score": 0.7873,
      "distance_km": 1.2
    }
  ]
}
```

**422** is returned for validation errors (e.g. empty `query`).

---

## POST `/api/chat`

Returns a single grounded, cited answer in the user's language.

**Request body**
```json
{ "query": "nearest open halal restaurant", "user_location": { "lat": 40.81, "lon": -74.07 } }
```

**200 response**
```json
{
  "answer": "Here is what I found:\n1. Halal Guys 8th Avenue — restaurant, open (9.1 km)",
  "language": "en",
  "citations": [ { "event_id": "nyc-halal-cart-8th", "name": "Halal Guys 8th Avenue" } ],
  "results": [ { "event": { "...": "..." }, "score": 0.79, "distance_km": 9.1 } ]
}
```

---

## POST `/api/chat/stream`

Same inputs as `/chat`, streamed as **Server-Sent Events**.

**Event sequence**
```
event: language
data: en

event: token
data: Here is what I found:

event: token
data: 1. Halal Guys 8th Avenue — restaurant, open (9.1 km)

event: done
data: {"citations": [...], "results": [...]}
```

Consume with `EventSource` or any SSE client. The `done` event carries the citations and
full result payload as a JSON string.

---

## Error model

| Status | Meaning |
|-------:|---------|
| 422 | Request body failed validation |
| 500 | Unhandled server error |

In real mode, transient upstream failures (Elastic MCP or Gemini) degrade gracefully: the
agent falls back to deterministic planning/answering rather than returning an error, so
the user always receives a usable response.

---

## GET `/api/ready`

Readiness probe (distinct from `/health` liveness). Runs dependency health checks and
returns **200** when ready, **503** when any critical dependency is unhealthy.

```json
{
  "state": "healthy",
  "ready": true,
  "components": [
    { "name": "search", "state": "healthy", "detail": "indices reachable", "latency_ms": 0.4 },
    { "name": "events_repo", "state": "healthy", "detail": "16 events", "latency_ms": 0.1 }
  ]
}
```

## GET `/api/metrics`

Prometheus text-format metrics (request counts, latency histograms, cache/circuit gauges).

## GET `/api/analytics`

Aggregated query analytics snapshot.

```json
{
  "total": 42,
  "zero_result": 3,
  "zero_result_rate": 0.0714,
  "by_language": { "en": 30, "es": 9, "fr": 3 },
  "by_category": { "restaurant": 18, "transit": 11 },
  "top_queries": [["halal food open now", 7], ["nearest transit", 5]]
}
```

## POST `/api/routes`

Compute route options between two points — the "cheapest route to the stadium now" use
case. `modes` is optional (defaults to walk/transit/drive).

**Request**
```json
{
  "origin": { "lat": 40.8135, "lon": -74.0745 },
  "destination": { "lat": 40.758, "lon": -73.985 },
  "modes": ["walk", "transit", "drive"]
}
```

**200 response**
```json
{
  "options": [
    { "mode": "drive", "total_distance_km": 9.7, "total_duration_min": 16.6, "estimated_cost": 12.2, "currency": "USD", "legs": [ ... ] }
  ],
  "cheapest": { "mode": "walk", "estimated_cost": 0.0, "...": "..." },
  "fastest": { "mode": "drive", "total_duration_min": 16.6, "...": "..." }
}
```

---

## POST `/api/search` — pagination

`/search` accepts an optional `cursor` (opaque, tamper-evident). When supplied, the
response includes `next_cursor` and `total` for load-more paging:

```json
{ "query": "open", "top_k": 3, "cursor": "eyJvIjowLCJjIjoi..." }
```
Response adds `"next_cursor"` (null at the end) and `"total"`.

## POST `/api/search/batch`

Run several queries in one call (max 20).

```json
{ "queries": ["stadium", "transit"], "top_k": 3 }
```
Returns `{ "responses": [ <SearchResponse>, ... ] }`.

## Saved searches

- `POST /api/saved-searches` — body `{ owner, query, label, tags? }` → created search.
- `GET /api/saved-searches/{owner}/{id}` — fetch one (404 problem if missing).
- `DELETE /api/saved-searches/{owner}/{id}` — delete (404 problem if missing).

Saved searches are owner-scoped and backed by a versioned repository with optimistic
concurrency.

## GET `/api/flags`

Evaluated feature flags: `{ "flags": { "reranking": true, "route_enrichment": true, ... } }`.

## GET `/api/traces`

Most recent spans (for debugging): `trace_id`, `span_id`, `parent_id`, `name`,
`duration_ms`, `status`, `attributes`.

## Admin / ops

- `GET /api/admin/status` — events count, cache size/hit-rate, data staleness, flags.
- `POST /api/admin/cache/flush` — clear the search cache, returning prior stats.
- `POST /api/admin/reindex` — re-run ingestion into the event repository.

These are protected by API-key auth when keys are configured.

---

## Governance & ops endpoints (v1.4.0)

### GET `/api/audit`
Recent audit entries plus chain-integrity status: `{ "verified": true, "count": N,
"entries": [ { seq, actor, tenant, action, resource, outcome, ts } ] }`.

### POST `/api/webhooks`
Register a subscriber. Body `{ tenant, url, secret (≥8 chars), events: [..] }` →
`{ id, events }`. Deliveries are HMAC-SHA256 signed (`X-CC-Signature: sha256=...`).

### DELETE `/api/webhooks/{id}`
Remove a subscription (404 problem if unknown).

### GET `/api/usage/{tenant}`
Current-period usage: `{ tenant, period, count, by_action, remaining, quota }`. Exceeding
quota elsewhere yields a 429 `quota_exceeded` problem.

### GET `/api/gdpr/export/{subject}`
Export a subject's data: `{ subject, sessions, saved_searches, audit_entries }`.

### DELETE `/api/gdpr/{subject}`
Purge a subject's sessions and saved searches: `{ subject, sessions_removed,
saved_searches_removed }`.

### POST `/api/admin/reindex` — idempotency
Supply an `Idempotency-Key` header to make retries safe; a replay returns the prior result
with `"idempotent_replay": true`.

### Authorization model
Requests resolve to a principal (anonymous unless an API key maps to one). Built-in roles:
**visitor** (search/chat/route/save), **analyst** (+analytics/traces), **admin** (+cache,
reindex, webhooks, export, purge). The policy engine raises 403 `forbidden` when a
principal lacks a required permission.

---

## Scale & reliability endpoints (v1.5.0)

### GET `/api/version` (public)
Supported API versions: `{ "current": "v1", "supported": ["v1"] }`. Deprecated versions
return advisory `Deprecation` / `Sunset` headers.

### GET `/api/slo`
Per-service SLO status: `{ "services": [ { service, target, total, success_ratio,
meeting_slo, budget_remaining } ] }`.

### GET `/api/admin/outbox`
Outbox counts by state plus any dead letters: `{ "stats": { pending, delivered, failed,
dead }, "dead_letters": [ { id, topic, attempts, error } ] }`.

### GET `/api/admin/bulkhead`
Concurrency-limiter utilisation: `{ name, max_concurrent, active, queued, rejected }`.

### POST `/api/admin/retention/sweep`
Apply retention policies: `{ "swept": [ { name, removed } ] }`.

### Tenancy
`/api/usage/{tenant}` validates and normalises the tenant id (lower-cased; rejected with
400 `invalid_tenant` / `unknown_tenant` when malformed or outside the allow-list). A
`TenantContext` is propagated per request and namespaces scoped storage keys.

---

## Wiring & integration (v1.6.0)

### POST `/api/admin/outbox/relay`
Drains pending outbox messages to webhook subscribers (the relay step). Returns
`{ delivered, failed, dead }`. Published domain events (search performed, route requested,
zero result) are durably enqueued by the outbox bridge; this endpoint (or the scheduler in
production) delivers them — so a delivery failure retries rather than being lost.

### Reliability flow
```
agent → EventBus.publish(event)
      → OutboxBridge enqueues into Outbox (durable)
relay → Outbox.relay(WebhookOutboxSink)
      → WebhookDispatcher delivers to subscribers (HMAC-signed, retried, dead-lettered)
```
Search and chat retrieval now run behind a concurrency **bulkhead** (fast 503 when
saturated), and the **SLO tracker** records both successes and failures for accurate error
budgets.

---

## Temporal availability & live signals (S73)

The product's time-sensitive queries ("open *now*", "route to the stadium *now*") are backed
by a real availability layer: timezone-aware opening hours (with overnight windows, holiday
/ match-day overrides) joined with fast-changing live signals (crowd, wait, transient
closure) that decay toward "unknown" as they age. These signals also feed the reranker, which
demotes crowded, closing-soon, and temporarily-closed venues.

### GET `/api/availability/{venue_id}`

Resolve a venue's combined opening-hours + live availability.

Query params:
- `at` *(optional)* — ISO-8601 instant (e.g. `2026-06-02T20:30:00Z`). Defaults to now.

Response:
```json
{
  "venue_id": "nyc-halal-cart-8th",
  "open_state": "closing_soon",
  "is_open": true,
  "effectively_open": true,
  "minutes_to_transition": 20,
  "crowd": "busy",
  "wait_minutes": 15,
  "temporarily_closed": false,
  "note": ""
}
```
- `open_state` ∈ `open` | `closed` | `opening_soon` | `closing_soon`.
- `effectively_open` = open per the schedule **and** not under a trusted transient closure.
- `minutes_to_transition` = minutes to close (if open) or to open (if closed), or `null`.
- A malformed `at` returns `422` (validation error).

### POST `/api/availability/signals`

Report a live operational signal for a venue.

Request:
```json
{
  "venue_id": "nyc-fan-zone-central",
  "crowd": "packed",
  "wait_minutes": 30,
  "temporarily_closed": false,
  "note": "match crowd"
}
```
- `crowd` ∈ `quiet` | `moderate` | `busy` | `packed` | `unknown`; an invalid value → `422`.
- `observed_at` *(optional)* — defaults to now; older reports never override newer ones.
- Returns the freshly-resolved `VenueAvailability` (same shape as the GET).
