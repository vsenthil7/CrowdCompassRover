# CrowdCompass Rover — Operations Runbook

**Version:** 1.0 | **Last updated:** 2026-06-03

This runbook covers the operational procedures for running CrowdCompass Rover in
production (Cloud Run + Elasticsearch + Gemini). In mock mode none of the external
dependencies are required; the procedures below apply to `APP_MODE=real` / `hybrid`
deployments. Replace `YOUR_URL` with the service URL and `$ADMIN_KEY` with an admin
API key.

---

## 1. API Key Rotation

**When:** a key is suspected compromised, or on the 90-day rotation schedule.

API keys are supplied via the `API_KEYS` setting (comma-separated). Any configured key is
granted the admin role by the composition root, so treat them as privileged secrets.

```bash
# 1. Generate a new key.
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Add it alongside the existing key(s) so there is no downtime
#    (API_KEYS accepts a comma-separated list — old and new valid simultaneously).
#    On Cloud Run this is a Secret Manager value; update it and roll a new revision.

# 3. Verify the new key works BEFORE removing the old one.
curl -sf https://YOUR_URL/api/admin/status -H "X-API-Key: $NEW_KEY" >/dev/null && echo OK

# 4. Remove the old key from API_KEYS and roll another revision.
# 5. Confirm the old key is now rejected.
curl -s -o /dev/null -w "%{http_code}" https://YOUR_URL/api/admin/status \
  -H "X-API-Key: $OLD_KEY"   # expect 403
```

**Rollback:** re-add the old key to `API_KEYS` and redeploy.

---

## 2. Dependency Unhealthy / Circuit Breaker Open

**Symptom:** `GET /api/ready` returns 503; search latency spikes or errors.

The search path is wrapped by a resilient provider (retry + circuit breaker) and a
concurrency bulkhead. When a dependency (Elastic / Gemini) is failing, the breaker opens and
the system serves fast failures instead of piling up.

```bash
# Which dependency is unhealthy?
curl -s https://YOUR_URL/api/ready | python3 -m json.tool

# Bulkhead saturation / rejections:
curl -s https://YOUR_URL/api/admin/bulkhead -H "X-API-Key: $ADMIN_KEY" | python3 -m json.tool
```

**Actions:**
- If Elastic is down: the provider falls back to the in-memory seed corpus (mock path) so
  search keeps returning results; investigate the cluster, then let the breaker half-open.
- If Gemini is down: answers fall back to the deterministic mock answerer; results are still
  grounded in retrieved venues.
- If the bulkhead shows sustained rejections: scale out replicas or raise the concurrency
  cap; do not remove the bulkhead (it is what prevents cascading failure).

---

## 3. Webhook Delivery Failures

**Symptom:** subscribers not receiving events; dead-letter count rising.

Delivery runs through a transactional outbox: events are enqueued durably, then relayed to
HMAC-signed subscribers with retry and dead-lettering.

```bash
# Outbox health (pending / delivered / failed / dead):
curl -s https://YOUR_URL/api/admin/outbox -H "X-API-Key: $ADMIN_KEY" | python3 -m json.tool

# Force a relay pass:
curl -s -X POST https://YOUR_URL/api/admin/outbox/relay -H "X-API-Key: $ADMIN_KEY"
```

**Common causes:**
- Subscriber URL rejected by the SSRF guard (loopback/private/metadata) — fix the URL; these
  are blocked by design.
- Subscriber returning non-2xx — check the subscriber; messages dead-letter after max retries.
- Signature mismatch — confirm the subscriber uses the shared secret to verify the HMAC.

---

## 4. Tenant Isolation Verification

**When:** after onboarding a tenant, or investigating a suspected data-leak report.

Event-repository keys are scoped by the active tenant (`"{tenant_id}::{key}"`), so reads are
structurally isolated.

```bash
# Per-tenant usage and quota:
curl -s https://YOUR_URL/api/usage/TENANT_ID -H "X-API-Key: $ADMIN_KEY" | python3 -m json.tool
```

If a cross-tenant read is ever observed, treat it as a Sev-1: capture the request id (every
response carries `X-Request-Id`), check the audit log, and verify the tenant context
middleware is populating the request scope.

---

## 5. Audit Chain Integrity

**When:** routine compliance check, or after any suspected tampering.

The audit log is hash-chained (each entry binds the previous hash). Verification tolerates a
retention-pruned prefix (it validates from the first retained entry).

```bash
# verified=true means the chain is intact.
curl -s https://YOUR_URL/api/audit -H "X-API-Key: $ADMIN_KEY" \
  | python3 -c "import sys,json; print('verified:', json.load(sys.stdin)['verified'])"
```

If `verified` is false: freeze writes, snapshot the current log, and investigate — a broken
chain indicates either data corruption or tampering. Do not truncate or "repair" the log.

---

## 6. Retention Sweep

**When:** scheduled data-minimisation, or storage pressure.

```bash
curl -s -X POST https://YOUR_URL/api/admin/retention/sweep -H "X-API-Key: $ADMIN_KEY" \
  | python3 -m json.tool   # returns per-source removal counts
```

The sweep prunes analytics/audit per policy. The audit chain remains verifiable after a
prefix prune (see procedure 5).

---

## 7. GDPR Data-Subject Requests

```bash
# Export everything held about a subject:
curl -s https://YOUR_URL/api/gdpr/export/SUBJECT_ID -H "X-API-Key: $ADMIN_KEY"

# Erase a subject (purges identifying fields, preserves the audit chain, emits an event):
curl -s -X DELETE https://YOUR_URL/api/gdpr/SUBJECT_ID -H "X-API-Key: $ADMIN_KEY"
```

Erasure requires the `PURGE_DATA` permission and export requires `EXPORT_DATA`; both are
admin-only by default.

---

## 8. Health & Readiness Reference

- `GET /api/health` — liveness (process up). Used by the container HEALTHCHECK.
- `GET /api/ready` — readiness; per-dependency detail (Elastic, Gemini, cache, tracer).
  Returns its body on both 200 and 503 so dashboards can show *why* it is not ready.
- `GET /api/metrics` — Prometheus text format, including p50/p95/p99 latencies.

**Deploy note:** the backend image runs as a non-root user and exposes port 8000; the
Cloud Run service should map secrets (API keys, Elastic/Gemini credentials) via Secret
Manager references, never as plain-text environment values.
