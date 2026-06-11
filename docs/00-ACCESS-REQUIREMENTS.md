# CrowdCompass Rover — Access & Credentials Requirements

**Project:** Google Cloud Rapid Agent Hackathon (AT-Hack0025)
**Track:** T2 — Elastic · **Product:** P1 — CrowdCompass Rover
**Document:** `docs/00-ACCESS-REQUIREMENTS.md`
**Last updated:** 2026-06-01

This document lists every external credential / access grant the product needs to run
against **real** services. Until each is provided, the corresponding subsystem runs in
**MOCK mode** (deterministic, offline). All code paths are written so that flipping an
environment variable switches MOCK → REAL with **no code change**.

---

## 1. Access Matrix

| # | System | Why needed | Env var(s) | Status | Fallback when absent |
|---|--------|-----------|------------|--------|----------------------|
| 1 | **Elasticsearch** (Serverless or 8.x) | Hybrid keyword+vector+geo store for city/event data | `ELASTIC_URL`, `ELASTIC_API_KEY` | ⏳ Pending | In-memory mock index w/ fixture data |
| 2 | **Elasticsearch MCP server** | Agent tool surface (`list_indices`, `get_mappings`, `search`, `esql`) | `ELASTIC_MCP_URL`, `ELASTIC_MCP_API_KEY` | ⏳ Pending | Local mock MCP server (same JSON-RPC contract) |
| 3 | **Google Cloud project** | Hosting + Agent Builder + Cloud Run | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS` | ⏳ Pending | Not required for local dev |
| 4 | **Gemini API (Vertex AI / AI Studio)** | Agent reasoning + multilingual NL→query | `GEMINI_API_KEY` or Vertex SA | ⏳ Pending | Deterministic mock planner/LLM |
| 5 | **Google Maps / Routes API** (optional) | "cheapest route to stadium now" enrichment | `GOOGLE_MAPS_API_KEY` | ⏳ Optional | Synthetic distance/time from fixtures |
| 6 | **Translation** (optional; Gemini covers most) | Edge-case language fallback | uses `GEMINI_API_KEY` | ⏳ Optional | Pass-through + mock detect |

Legend: ✅ Provided · ⏳ Pending · ❌ Not available

---

## 2. How MOCK / REAL switching works

A single setting drives everything:

```
APP_MODE=mock   # default — fully offline, deterministic, used in CI & Playwright
APP_MODE=real   # uses live Elastic MCP + Gemini; requires creds above
APP_MODE=hybrid # real Elastic, mock LLM (or vice-versa) for partial testing
```

Each integration is behind a provider interface (`backend/app/services/*`), selected at
runtime by a factory in `backend/app/core/providers.py`. The same test suite runs in
`mock` (always, in CI) and can be re-run in `real`/`hybrid` once Claude Desktop has the
credentials, with **zero code edits** — only env vars change.

---

## 3. What to hand over when access is available

1. An Elasticsearch deployment URL + API key with index create/read/write.
2. The Elastic MCP server endpoint URL + API key (or run it locally pointed at #1).
3. A Gemini API key (AI Studio) **or** a Vertex AI service-account JSON + project id.
4. (Optional) Google Maps Routes API key.

Drop them into `backend/.env` (template at `backend/.env.example`) and set
`APP_MODE=real`. Then `make seed && make test-real`.

---

## 4. Security notes

- No secret is ever committed; `.env` is git-ignored, only `.env.example` is tracked.
- API keys are read once at startup into a typed `Settings` object (pydantic-settings).
- The mock MCP server binds to localhost only.
- All inbound API requests are schema-validated; query DSL is built server-side (no raw
  user DSL passthrough) to prevent injection into Elasticsearch.
