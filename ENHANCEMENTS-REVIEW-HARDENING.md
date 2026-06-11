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
