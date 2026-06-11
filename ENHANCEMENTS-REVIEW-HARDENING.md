# CrowdCompass Rover — Enhancement Summary (Perplexity Review Hardening: RBAC, Webhooks, Tenancy)

This round acts on the Perplexity V02 review playbook. It does **not** claim to complete the
whole playbook — large parts (live Elastic/Gemini credential validation, Firestore, Redis,
Cloud Run deploy, real webhook delivery to live endpoints, load tests) require infrastructure
this sandbox does not have. Instead it closes the **highest-value gaps that are real,
sandbox-runnable, and were genuinely broken** — the ones the reviewer flagged as "built but
unused / stubbed."

## Gaps closed (all verified by running)

### 1. RBAC enforcement at the route layer (playbook P3)
The reviewer's repo map said it plainly: `authz/rbac.py` and `authz/policy.py` were built,
the resolver + policy were wired into `Components`, but **no route enforced anything**.

- Added `get_principal` (resolve caller from `X-API-Key`) and `get_policy` FastAPI deps.
- Wired `policy.require(principal, Permission.X)` into every elevated route: analytics,
  traces, all `/admin/*`, webhook create/delete, GDPR export/purge, outbox relay, retention
  sweep, and chat-stream.
- Added a configurable `rbac_public_baseline` (default on) so public search/chat/route stay
  zero-config in mock mode (preserving the demo and all existing tests), while privileged
  routes are genuinely gated. With the baseline off, even search requires a permission.
- **Negative tests** prove it: every elevated route returns `403 forbidden` to a
  permissionless caller and `200` with an admin key; a bogus key is treated as anonymous.

### 2. Real HTTP webhook sender + SSRF guard (playbook P5.S1)
The webhook "sender" was a no-op lambda returning `200`.

- New `app/webhooks/http_sender.py`: `HttpWebhookSender` performs a real httpx POST with a
  bounded timeout, behind `assert_safe_url()` which rejects non-https (unless explicitly
  allowed), missing host, the cloud metadata address (169.254.169.254), and any host that
  resolves to a loopback / private / link-local / multicast / reserved IP.
- Wired into the composition root: live (real/hybrid) mode uses the real sender; mock mode
  keeps the offline sender. The dispatcher's `(url, headers, body) -> status` contract is
  unchanged, so the existing retry / dead-letter / outbox machinery is untouched.
- Tests cover every SSRF rejection branch, a successful signed delivery via an injected
  `httpx.MockTransport` (no real network), and the mode-based wiring.

### 3. Tenant key-scoping across stores (playbook P4.S5)
`TenantContext.scoped_key()` and `TenantScopedStore` existed but were **not wired** to the
repositories, so cross-tenant isolation was not actually enforced.

- `InMemoryEventRepository` now scopes every key by the active tenant
  (`"{tenant_id}::{key}"`). All of get / put / bulk_put / list_all / by_city / count / delete
  filter by the current tenant's prefix. No active context defaults to `default`; fixtures
  seed under `default`.
- **Isolation tests** prove a tenant cannot read, list, count, or delete another tenant's
  data, and that seed data is visible only under `default`.

## Verification (reproducible)

```bash
cd backend && pip install -e ".[dev]" && python -m pytest   # 552 passed, 100% coverage
cd ../frontend && npm install && npx vitest run             # 174 passed, 100%
npm run build                                               # clean
```

Result: **backend 552 tests @ 100% (up from 499), frontend 174 @ 100%, build clean.**

## Honest status on the rest of the playbook

Still open and **infra-dependent** (cannot be closed in this sandbox without credentials /
cloud): live Elastic + Gemini integration tests, Elastic seed/bulk-index against a real
cluster, Firestore durable persistence, Redis shared quotas, Cloud Run deploy + Secret
Manager, real webhook delivery to a live endpoint, load tests, SBOM/CI on a real runner.

Still open but **sandbox-feasible** (good next targets, no infra needed): P2.S1
`put_mapping`/`bulk_index` on the MCP client (mockable), P1 Dockerfiles + compose as
artifacts, and several P6/P7 width modules (intent analytics API, relevance-tuning weights
endpoint, geofence point-in-polygon). These are pure code + tests and would extend coverage
the same way this round did.

The honest bar remains: this is mock-first with live integrations by config. This round made
the security and multi-tenancy posture real (enforced, not just present), which is the part
of "enterprise-grade" most worth fixing first.

---

## Round 2 — Deployment + integration artifacts (sandbox-feasible playbook steps)

Continuing the same playbook, this round closed every remaining step that does **not** need
live cloud/credentials:

- **P2.S1** — `ElasticMCPClient` gained `put_mapping`, `delete_index`, `bulk_index`, `count`
  (the methods the Elastic seed/bootstrap path requires). Transport-stub tests assert the
  exact MCP tool name + arguments and the response parsing.
- **P2.S3** — `build_query` deepened to Elasticsearch 8.x Reciprocal Rank Fusion
  (`rank.rrf`), a soft `open_now` boost (a `should` clause — boost, never a hard filter), and
  injectable keyword/vector weights so a relevance-tuning layer can override them. Existing
  query-shape tests still pass; new tests cover RRF, the boost, weight passthrough, and the
  kNN-`k` window cap.
- **P1.S1-S3** — multi-stage non-root backend `Dockerfile`; nginx-served frontend
  `Dockerfile` + `nginx.conf`; root `docker-compose.yml` (backend + frontend by default; ES +
  Redis + hybrid backend behind a `--profile live`). All valid; building/running is
  environment-gated (no Docker daemon here).
- **P5.S3** — `docs/06-RUNBOOK.md` (164 lines): key rotation, breaker/bulkhead response,
  webhook/outbox triage, tenant-isolation + audit-chain verification, retention, GDPR.
- **P6.S1** — enhanced `.github/workflows/ci.yml`: lint + pip-audit, backend 100% gate,
  frontend coverage, e2e, Docker build + container smoke-test, CycloneDX SBOM on release, and
  an opt-in live-integration job gated on repository secrets.
- **C4** — `cyclonedx-bom` + `pip-audit` added to dev deps; `Makefile` `sbom` / `pip-audit`
  targets. SBOM generation was run locally and verified (189 components, schema-valid).

**Backend 552 -> 565 tests, still 100% coverage. Frontend 174 @ 100%.**

### Still infra-blocked (cannot complete in this sandbox, need real cloud/credentials)
P2.S2 / P2.S4 (live Elastic seed + integration tests), P4.S1-S4 (Firestore, Redis quotas),
P5.S2 / C2 (Secret Manager), C5 (load test), C6 (DR/backup), C7 (PagerDuty/Slack), and the
Section-7 "definition of done" items that require `docker compose up`, `gcloud run`,
`APP_MODE=real` passes, or a CI runner. The Dockerfiles, compose, CI, runbook, and SBOM
tooling above are exactly what those steps consume once an environment exists.

---

## Round 3 — Remaining sandbox-feasible width modules

This round closed every remaining playbook step that needs no live cloud/credentials:

- **P4.S1** persistence/Redis/GCP/residency settings.
- **P6.S7** geofence ray-casting point-in-polygon + per-tenant registry.
- **P6.S11 / P7.S3** A/B answer-quality eval framework (models, registry, runner; judge
  optional, fully usable in mock mode).
- **P6.S3 / P7.S4** relevance-tuning config + injectable store + `GET`/`PUT
  /admin/relevance/weights` (feeds the RRF query builder's tunable weights).
- **P6.S5** OIDC/JWT resolver (JWKS injectable; offline-tested with a self-signed RS256 key).
- **P6.S8** partner connector framework (spec/status, REST connector with injectable
  transport, `map_record` normaliser, per-tenant registry).
- **P6.S10 / P7.S2** intent analytics over the real event log + `GET /analytics/intents`.
- **P1.S4** Cloud Run `service.yaml` + `cloudbuild.yaml` (Secret Manager refs, no plaintext).
- **P6.S4** saved-search alerter (diff open_now results, fire `saved_search.alert` webhook).
- **P6.S9 / P7.S1** multilingual CMS store + admin API (6 real locales).
- **P6.S6** WCAG 2.2 AA ARIA remediation + `@axe-core/playwright` accessibility spec.

**Backend 565 -> 641 tests, still 100% coverage. Frontend 174 @ 100%, build clean.**

### Honest final status: 26 of 38 playbook steps complete
The remaining 12 require a real environment to *execute/verify* and cannot be truthfully
ticked in this sandbox: **P2.S2** (seed a live Elastic cluster), **P2.S4** (live
Elastic+Gemini integration tests), **P4.S2** (Firestore repo), **P4.S3** (wire durable
adapters), **P4.S4** (Redis-backed limiter/quotas), **P5.S2 / C2** (GCP Secret Manager),
**C5** (load test), **C6** (DR/backup), **C7** (PagerDuty/Slack), and the Section-7
"Definition of Done" checklist (needs `docker compose up`, `gcloud run`, `APP_MODE=real`
passes, and a CI runner). The Dockerfiles, compose, Cloud Run YAML, CI workflow, runbook, and
SBOM tooling already in the repo are exactly what those steps consume once credentials and a
deploy target exist.
