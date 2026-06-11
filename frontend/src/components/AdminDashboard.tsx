import type { AdminStatus, AuditReport } from "../lib/types";
import { UsageView } from "./UsageView";
import { formatAge, formatPercent, onActivate } from "../lib/a11y";
import type { UsageInfo } from "../lib/types";

interface Props {
  status: AdminStatus | null;
  usage: UsageInfo | null;
  audit: AuditReport | null;
  loading: boolean;
  busy: boolean;
  error: string | null;
  onRefresh: () => void;
  onReindex: () => void;
  onFlush: () => void;
}

export function AdminDashboard({
  status,
  usage,
  audit,
  loading,
  busy,
  error,
  onRefresh,
  onReindex,
  onFlush,
}: Props) {
  return (
    <section className="admin" data-testid="admin-dashboard" aria-label="Admin dashboard">
      <div className="admin__head">
        <h2 className="admin__title">Operations</h2>
        <span
          className="admin__refresh"
          role="button"
          tabIndex={0}
          onClick={onRefresh}
          onKeyDown={onActivate(onRefresh)}
          data-testid="admin-refresh"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </span>
      </div>

      {error ? (
        <div className="error" data-testid="admin-error">
          {error}
        </div>
      ) : null}

      {status ? (
        <div className="admin__grid" data-testid="admin-status">
          <div className="stat">
            <span className="stat__label">Events</span>
            <span className="stat__value">{status.events}</span>
          </div>
          <div className="stat">
            <span className="stat__label">Cache size</span>
            <span className="stat__value">{status.cache_size}</span>
          </div>
          <div className="stat">
            <span className="stat__label">Cache hit rate</span>
            <span className="stat__value">{formatPercent(status.cache_hit_rate)}</span>
          </div>
          <div className="stat">
            <span className="stat__label">Data age</span>
            <span className="stat__value">
              {formatAge(status.data_age_seconds)}
              {status.data_stale ? " (stale)" : ""}
            </span>
          </div>
        </div>
      ) : null}

      {usage ? <UsageView usage={usage} /> : null}

      <div className="admin__actions">
        <button className="btn" onClick={onReindex} disabled={busy} data-testid="admin-reindex">
          {busy ? "Working…" : "Reindex"}
        </button>
        <button className="btn btn--ghost" onClick={onFlush} disabled={busy} data-testid="admin-flush">
          Flush cache
        </button>
      </div>

      {audit ? (
        <div className="admin__audit" data-testid="admin-audit">
          <h3 className="admin__subtitle">
            Audit log{" "}
            <span className={audit.verified ? "audit-ok" : "audit-bad"} data-testid="audit-integrity">
              {audit.verified ? "✓ verified" : "✗ tampered"}
            </span>
          </h3>
          <ul className="admin__audit-list">
            {audit.entries.slice(-5).reverse().map((e) => (
              <li key={e.seq} data-testid="audit-row">
                #{e.seq} {e.action} → {e.resource} ({e.outcome})
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
