import type { ReadinessReport } from "../lib/types";

interface Props {
  readiness: ReadinessReport;
}

/** Dependency readiness: the per-component checks behind /ready (Elastic, Gemini,
 *  etc.), with overall ready/not-ready state. Surfaces the backend HealthRegistry
 *  that previously had no UI beyond a single liveness dot. */
export function HealthPanel({ readiness }: Props) {
  const { ready, state, components } = readiness;
  return (
    <div className="health" data-testid="health-panel" aria-label="Dependency readiness">
      <div className="health__head">
        <span
          className={ready ? "health__overall health__overall--ok" : "health__overall health__overall--bad"}
          data-testid="health-overall"
          data-ready={ready ? "true" : "false"}
        >
          {ready ? "READY" : "NOT READY"}
        </span>
        <span className="health__state">{state}</span>
      </div>
      {components.length === 0 ? (
        <p className="health__empty" data-testid="health-empty">No dependency checks registered.</p>
      ) : (
        <ul className="health__list" data-testid="health-list">
          {components.map((c) => (
            <li key={c.name} className="health__row" data-testid={`health-row-${c.name}`}>
              <span
                className={c.state === "healthy" ? "health__dot health__dot--ok" : "health__dot health__dot--bad"}
                aria-hidden="true"
              />
              <span className="health__name">{c.name}</span>
              <span className="health__detail">{c.detail || c.state}</span>
              <span className="health__latency">{c.latency_ms.toFixed(1)} ms</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
