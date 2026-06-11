# CrowdCompass Rover — Live Integration Test Findings (T2-Elastic)

**Date:** 2026-06-11
**Tester:** Claude (automated, against real local Docker stack)
**Repo:** https://github.com/vsenthil7/CrowdCompassRover

## What was stood up (real, not mocked)

| Component | Image / Version | Status |
|---|---|---|
| Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:8.13.0` | Up, cluster health **green** (single node) |
| Redis | `redis:7.2-alpine` | Up, **healthy** |
| Elastic MCP server | `docker.elastic.co/mcp/elasticsearch:latest` (v0.4.6), streamable-HTTP on `:9201/mcp` | Up; `tools/list` verified |

All three were exercised over the real network: app → Elastic MCP server (`/mcp` JSON-RPC) → Elasticsearch.

## Test results (mock mode — the default CI path)

| Suite | Result | Coverage |
|---|---|---|
| Backend `pytest` | **641 passed, 8 deselected** | **100.00%** (4407/4407 stmts, `--cov-fail-under=100` enforced) |
| Frontend `vitest` | **174 passed** | **100%** stmts/branch/funcs/lines |
| E2E Playwright (chromium) | **10 passed** (8 journeys + 2 WCAG 2.2 AA) | after fixing `getByLabelText`→`getByLabel` bug |

Mock-mode quality is genuinely excellent. The findings below concern only the **live** integration path.

## Live integration findings (INT-01 — Elasticsearch via MCP)

Running `tests/integration/test_elastic_live.py` against the real stack: **2 failed in 10s** (did not hang, did not skip). Two distinct, independent root causes:

### Finding 1 — Stale test: `QueryPlan` missing required fields (test-code bug)
`test_hybrid_rrf_query_executes` constructs `QueryPlan(normalized_query=..., semantic_text=..., filters=..., top_k=...)` but the current model also requires `original_query` and `detected_language`. Result: `pydantic ValidationError: 2 validation errors for QueryPlan` before the query is ever sent. The integration test was not updated when the model gained those fields.

### Finding 2 — MCP contract mismatch: app assumes write tools the real server doesn't expose (app bug)
The official Elastic MCP server (`tools/list`, verified live) exposes exactly **5 read-only tools**:
`esql`, `search`, `list_indices`, `get_shards`, `get_mappings` — all annotated `readOnlyHint: true`.

`app/mcp/elastic_client.py` calls tools that **do not exist** on the real server:
- `create_index` (used by `put_mapping`)
- `bulk` (used by `bulk_index`)
- `count`
- `delete_index`

It also mismatches the one shared tool:
- App's `search` sends `{"index", "query"}`; the real `search` tool requires `{"index", "query_body"}`.
- App's `list_indices` sends `{}`; the real tool **requires** an `index_pattern` argument.

So `test_put_mapping_and_count` (which calls `delete_index`/`put_mapping`/`bulk_index`/`count`) cannot succeed against the official MCP server regardless of how ES is configured — the server is read-only by design and has no write tools.

## Why this matters / interpretation

- The **unit-tested** `ElasticMCPClient` passes 100% because it's tested against a *stubbed* transport that mirrors the app's *assumed* contract. The assumed contract diverges from the *real* Elastic MCP server. This is the classic mock-drift gap.
- This does **not** indicate the mock-mode product is broken — that path is fully green. It means the **live Elastic wiring needs reconciliation** before it can run end-to-end.

## Recommended remediation (needs a scope decision)

1. **Indexing path:** the official Elastic MCP server is read-only. Seeding/bulk-indexing must go **directly to the Elasticsearch REST API / official ES client**, not through the MCP server. Split responsibilities: ES client for writes (ingestion/seed), MCP `search`/`esql` for the agent read path.
2. **Search params:** rename the app's `search` argument `query` → `query_body`; pass `index_pattern` to `list_indices`.
3. **Fix the stale test:** add `original_query` and `detected_language` to the `QueryPlan` in `test_hybrid_rrf_query_executes`.
4. Re-run `pytest -m integration` against this same local stack to confirm green.

> The 8 `integration`-marked tests are correctly **deselected** from the 100% gate and correctly **skip** when creds are absent — they never fabricate a pass. That design is sound; the tests/contract behind them need the fixes above.

## Reproduce

```bash
docker compose --profile live up -d elasticsearch redis
docker run -d --name ccr-es-mcp --network <project>_default -p 9201:8080 \
  -e ES_URL=http://elasticsearch:9200 -e CONTAINER_MODE=true \
  docker.elastic.co/mcp/elasticsearch:latest http --address 0.0.0.0:8080
cd backend
ELASTIC_MCP_URL=http://localhost:9201 ELASTIC_MCP_API_KEY=none ELASTIC_INDEX=cc-city-events \
  pytest -m integration tests/integration/test_elastic_live.py -rA
```
