import type {
  AdminStatus,
  AnalyticsSnapshot,
  AuditReport,
  BulkheadStats,
  FlagsReport,
  OutboxStats,
  ReadinessReport,
  SloReport,
  TracesReport,
  VersionInfo,
} from "../lib/types";
import { UsageView } from "./UsageView";
import { SloPanel } from "./SloPanel";
import { VersionBadge } from "./VersionBadge";
import { OutboxPanel } from "./OutboxPanel";
import { AnalyticsPanel } from "./AnalyticsPanel";
import { TracesPanel } from "./TracesPanel";
import { FlagsPanel } from "./FlagsPanel";
import { HealthPanel } from "./HealthPanel";
import { BulkheadPanel } from "./BulkheadPanel";
import { formatAge, formatPercent, onActivate } from "../lib/a11y";
import type { UsageInfo } from "../lib/types";

interface Props {
  status: AdminStatus | null;
  usage: UsageInfo | null;
  audit: AuditReport | null;
  slo: SloReport | null;
  version: VersionInfo | null;
  outbox: OutboxStats | null;
  analytics?: AnalyticsSnapshot | null;
  traces?: TracesReport | null;
  flags?: FlagsReport | null;
  readiness?: ReadinessReport | null;
  bulkhead?: BulkheadStats | null;
  loading: boolean;
  busy: boolean;
  error: string | null;
  onRefresh: () => void;
  onReindex: () => void;
  onFlush: () => void;
  onRelay: () => void;
  onSweepRetention: () => void;
}

export function AdminDashboard({
  status,
  usage,
  audit,
  slo,
  version,
  outbox,
  analytics = null,
  traces = null,
  flags = null,
  readiness = null,
  bulkhead = null,
  loading,
  busy,
  error,
  onRefresh,
  onReindex,
  onFlush,
  onRelay,
  onSweepRetention,
}: Props) {
  return (
    <section className="admin" data-testid="admin-dashboard" aria-label="Admin dashboard">
      <div className="admin__head">
        <h2 className="admin__title">Operations</h2>
        {version ? <VersionBadge version={version} /> : null}
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

      {slo ? (
        <div className="admin__slo" data-testid="admin-slo">
          <h3 className="admin__subtitle">Service objectives</h3>
          <SloPanel slo={slo} />
        </div>
      ) : null}

      {readiness ? (
        <div className="admin__section" data-testid="admin-health">
          <h3 className="admin__subtitle">Dependency readiness</h3>
          <HealthPanel readiness={readiness} />
        </div>
      ) : null}

      {bulkhead ? (
        <div className="admin__section" data-testid="admin-bulkhead">
          <h3 className="admin__subtitle">Concurrency</h3>
          <BulkheadPanel bulkhead={bulkhead} />
        </div>
      ) : null}

      {analytics ? (
        <div className="admin__section" data-testid="admin-analytics">
          <h3 className="admin__subtitle">Query analytics</h3>
          <AnalyticsPanel analytics={analytics} />
        </div>
      ) : null}

      {flags ? (
        <div className="admin__section" data-testid="admin-flags">
          <h3 className="admin__subtitle">Feature flags</h3>
          <FlagsPanel flags={flags} />
        </div>
      ) : null}

      {traces ? (
        <div className="admin__section" data-testid="admin-traces">
          <h3 className="admin__subtitle">Recent traces</h3>
          <TracesPanel traces={traces} />
        </div>
      ) : null}

      {outbox ? <OutboxPanel outbox={outbox} onRelay={onRelay} busy={busy} /> : null}

      <div className="admin__actions">
        <button className="btn" onClick={onReindex} disabled={busy} data-testid="admin-reindex">
          {busy ? "Working…" : "Reindex"}
        </button>
        <button className="btn btn--ghost" onClick={onFlush} disabled={busy} data-testid="admin-flush">
          Flush cache
        </button>
        <button className="btn btn--ghost" onClick={onSweepRetention} disabled={busy} data-testid="admin-sweep">
          Sweep retention
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
