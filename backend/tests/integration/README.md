# Integration tests (live services)

These tests exercise the **real** code paths against live Elastic, Gemini, GCP, and Redis.
They are marked `integration` and **deselected from the default test run** (`pyproject.toml`
sets `-m "not integration"`), so they never affect the 100% unit-coverage gate and never
fabricate a pass — without credentials they **skip**.

## Run them

```bash
# all integration tests (skips any whose env vars are unset)
pytest tests/integration -o addopts="" -m integration -v
```

## Required environment per step

| Test file | Playbook step(s) | Env vars |
|---|---|---|
| `test_elastic_live.py` | P2.S2, P2.S4 | `ELASTIC_MCP_URL`, `ELASTIC_MCP_API_KEY`, `ELASTIC_INDEX` |
| `test_gemini_live.py` | P2.S4 (Gemini) | `GEMINI_API_KEY` |
| `test_firestore_live.py` | P4.S2, P4.S3 | `GCP_PROJECT_ID` (+ `FirestoreEventRepository` implemented) |
| `test_redis_live.py` | P4.S4 | `REDIS_URL` (+ `RedisRateLimiter` implemented) |
| `test_secret_manager_live.py` | P5.S2, C2 | `GCP_PROJECT_ID` (+ `SecretManagerProvider` implemented) |

Tests for adapters that are not yet implemented (`firestore`, `redis_limiter`,
`gcp_secret_manager`) skip with a clear message until the module lands — at which point the
scaffold becomes their executable acceptance test.
