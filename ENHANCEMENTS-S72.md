# CrowdCompass Rover V07 — Enhancement Summary (Operator Observability)

This pass enhanced the **CrowdCompass Rover V07** build the same way the SpoofVane console
was enhanced: find where rich, tested backend depth is **not surfaced in the UI**, then wire
it in as proper modules while holding the 100% coverage bar on both sides.

## Starting point (verified, not assumed)

Unlike SpoofVane (a broken frontend over a good backend), Rover arrived genuinely mature.
Before touching anything I ran the suites and confirmed the README's claims were real:

- Backend: **436 tests, 100% coverage** (pytest-cov gate at `--cov-fail-under=100`).
- Frontend: **130 tests, 100% coverage** (vitest v8).
- Clean production build.

## The real gap

The backend exposes **30 HTTP endpoints**; the frontend consumed only **~13**. A whole
cluster of capabilities was built and tested but invisible to any operator — the same
"exists but not load-bearing in the UI" pattern the project itself had been hardening
against in sprints S68–S71. The unexposed, operator-facing ones:

| Endpoint | Capability | Before |
|----------|------------|--------|
| `GET /analytics` | query volume, zero-result rate, language/category breakdowns, top queries | no UI |
| `GET /traces` | recent distributed-tracing spans | no UI |
| `GET /flags` | evaluated feature flags | no UI |
| `GET /ready` | per-dependency readiness checks | only a single liveness dot |
| `GET /admin/bulkhead` | concurrency limiter utilisation | no UI |
| `POST /admin/retention/sweep` | retention TTL sweep | no UI |

## What was added (sprint S72)

All modular, matching the existing component/hook/style conventions:

- **`src/lib/api.ts`** — six typed client methods (`analytics`, `traces`, `flags`,
  `readiness`, `bulkheadStats`, `sweepRetention`) plus matching types in `types.ts`. The
  readiness client deliberately reads the JSON body on both 200 and 503, because `/ready`
  returns 503-with-body when a dependency is down.
- **Five panel components:**
  - `AnalyticsPanel` — stats row (with a high-zero-result warning), language/category
    breakdown chips, top-queries list.
  - `TracesPanel` — recent spans, child spans indented under parents, with a recursion
    guard that tolerates malformed cyclic trace data.
  - `FlagsPanel` — on/off feature-flag rows.
  - `HealthPanel` — overall READY/NOT-READY plus per-dependency rows with latency.
  - `BulkheadPanel` — active/capacity bar with ok/warning/critical saturation states.
- **`src/hooks/useAdmin.ts`** — loads all five surfaces in the `refresh` fan-out and adds a
  `sweepRetention` action (with the shared busy/error handling the other actions use).
- **`src/components/AdminDashboard.tsx`** — renders the five new sections and a "Sweep
  retention" control; wired through `App.tsx`.
- **CSS** — new panel styles using the existing design tokens (`--pitch`, `--amber`,
  `--alert`, `--ink-dim`, …).

## Tests (held the 100% bar)

- `tests/observability-panels.test.tsx` — every panel, all branches: empty states, each
  severity/utilisation class, the high-zero-result warning, orphan and **cyclic** trace
  parents (the recursion-guard branch), zero-capacity bulkhead.
- `tests/lib.test.ts` — the six new client methods, including the 503 readiness path.
- `tests/admin.test.tsx` — a populated-dashboard render that exercises all five sections and
  the sweep action, plus extended `useAdmin` coverage (new state on `refresh`,
  `sweepRetention` success + error).

## Verification (reproducible)

```bash
# backend (unchanged this pass, re-confirmed)
cd backend && pip install -e ".[dev]" && python -m pytest      # 436 passed, 100%

# frontend
cd frontend && npm install
npx vitest run --coverage   # 156 passed, 100% stmts/branches/funcs/lines
npm run build               # clean
```

Result: **backend 436 @ 100% (untouched), frontend 156 @ 100%, build clean.**

## Honest notes / limits

- This pass deliberately did not touch the backend — it was already at 100% and the gap was
  purely UI exposure. No new backend endpoints were needed; all six surfaced capabilities
  already existed and were tested.
- The new panels render live backend data through the existing `/api` client. In mock mode
  they show the deterministic mock/seed data; against a real Elastic/Gemini deployment they
  show live values — no code change, same provider-interface switch the project already uses.
- Playwright e2e remains as-is (browser execution is environment-blocked here); the new
  surfaces are covered by component + hook + client unit/integration tests.
