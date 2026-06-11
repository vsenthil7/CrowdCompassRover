import type { BulkheadStats } from "../lib/types";

interface Props {
  bulkhead: BulkheadStats;
}

/** Concurrency bulkhead utilisation: active vs capacity, queue depth, and
 *  rejected count. Surfaces the backend /admin/bulkhead limiter that fronts
 *  search/chat but previously had no UI. */
export function BulkheadPanel({ bulkhead }: Props) {
  const { name, max_concurrent, active, queued, rejected } = bulkhead;
  const utilisation = max_concurrent > 0 ? active / max_concurrent : 0;
  const cls =
    utilisation >= 1 ? "bulkhead-bar__fill--critical" : utilisation >= 0.7 ? "bulkhead-bar__fill--warning" : "bulkhead-bar__fill--ok";
  return (
    <div className="bulkhead" data-testid="bulkhead-panel" aria-label="Concurrency bulkhead">
      <div className="bulkhead__head">
        <span className="bulkhead__name">{name}</span>
        <span className="bulkhead__stat" data-testid="bulkhead-active">
          {active}/{max_concurrent} active
        </span>
      </div>
      <div
        className="bulkhead-bar"
        role="progressbar"
        aria-valuenow={active}
        aria-valuemax={max_concurrent}
      >
        <div className={`bulkhead-bar__fill ${cls}`} style={{ width: `${Math.min(100, utilisation * 100)}%` }} />
      </div>
      <div className="bulkhead__detail">
        {queued} queued{typeof rejected === "number" ? ` · ${rejected} rejected` : ""}
      </div>
    </div>
  );
}
