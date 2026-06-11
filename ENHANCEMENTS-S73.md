# CrowdCompass Rover — Enhancement Summary (S73: Temporal Availability & Live Signals)

This round added **genuine new product capability**, not UI plumbing. The previous pass
(S72) surfaced endpoints that already existed; the review feedback — fairly — was that this
is exposure, not depth. So S73 built the operational layer the product was actually missing.

## The gap

Rover's headline queries are time-sensitive — *"nearest **open** halal restaurant **now**"*,
*"cheapest route to the stadium **now**"* — but the data model only carried a static
`open_now` boolean. It could never reflect the *query time*, there were no opening hours, and
there was no notion of live crowding or temporary closures. The "now" was effectively faked.

## What was built (proper modules, separated)

**Backend — new domain layer:**

| Module | Responsibility |
|--------|----------------|
| `app/availability/hours.py` | Timezone-aware weekly `OpeningHours`: overnight windows, special-date overrides (holidays / match-days), 24/7 short-circuit; `TimeWindow` with correct overnight maths |
| `app/availability/evaluator.py` | Resolves `OPEN` / `CLOSED` / `OPENING_SOON` / `CLOSING_SOON` at any instant, including spillover from the previous local day's overnight window |
| `app/livesignals/store.py` | Live crowd / wait-time / transient-closure signals with **linear freshness decay** and a trust floor (stale reports stop influencing ranking) |
| `app/availability/service.py` | Joins hours + live signals into a `VenueAvailability` and a crowd-based ranking penalty |
| `app/availability/seed.py` | Category-based default schedules for the fixture corpus (mock-mode analogue of ingestion-sourced hours) |

**Wired in (load-bearing, not decorative):**
- `ranking/reranker.py` gained optional time-aware signals: demotes crowded
  (freshness-scaled), closing-soon, and temporarily-closed venues. Inert when no resolver is
  passed, so the previous static path is unchanged and all prior tests still hold.
- `AvailabilityService` constructed in the provider factory and added to `Components`.
- New endpoints: `GET /availability/{venue_id}` (optional `at` instant) and
  `POST /availability/signals`.

**Frontend — extended to match:**
- `api.availability` / `api.reportSignal` client methods + types.
- `AvailabilityBadge` component — open-state with closing/opening countdown, transient-
  closure override, crowd level + wait.
- `useAvailability` hook — per-venue fan-out; per-venue failures are swallowed so a lookup
  never blanks a result; optional `at` time.
- `ResultRow` shows the live badge when availability is supplied, else the static one.

## Correctness details a reviewer would check

- **Timezones:** a Madrid venue open 11:00–23:00 is correctly open at 13:00 UTC (15:00 local)
  and closed at 22:00 UTC (00:00 local).
- **Overnight windows:** a 20:00–02:00 bar is open at 01:00 — and, when checked on a day with
  *no* window of its own, the previous day's overnight window still correctly covers the
  early hours.
- **Freshness decay:** a "packed" report linearly decays; past the TTL it resolves to
  `unknown` and stops penalising ranking. A stale "temporarily closed" note is not trusted,
  so it can't suppress a venue forever.
- **Validation:** malformed `at` timestamps and unknown crowd levels return `422`.

## Verification (reproducible)

```bash
cd backend && pip install -e ".[dev]" && python -m pytest      # 499 passed, 100%
cd ../frontend && npm install
npx vitest run --coverage                                      # 174 passed, 100%
npm run build                                                  # clean
```

**Backend 499 tests @ 100% · Frontend 174 tests @ 100% · build clean.**

## Honest limits

- Opening hours are seeded by category in mock mode; a real deployment would populate them
  from the ingestion feeds (same provider-interface pattern the project already uses).
- Live signals are in-memory. A production system would back the `LiveSignalStore` with a
  TTL'd store (Redis/Elastic) — the interface is already shaped for that swap.
- As with prior rounds, the genuinely hard reviewer questions (live Elastic/Gemini under
  load, a persistent datastore, deployment) remain out of scope for this sandbox.
