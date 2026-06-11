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
