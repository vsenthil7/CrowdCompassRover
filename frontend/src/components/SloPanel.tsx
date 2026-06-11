import type { SloReport } from "../lib/types";
import { formatPercent } from "../lib/a11y";

interface Props {
  slo: SloReport;
}

function budgetClass(remaining: number): string {
  if (remaining <= 0) return "slo-bar__fill--critical";
  if (remaining < 0.5) return "slo-bar__fill--warning";
  return "slo-bar__fill--ok";
}

export function SloPanel({ slo }: Props) {
  if (slo.services.length === 0) {
    return (
      <p className="slo-empty" data-testid="slo-empty">
        No SLO data yet — run a few searches.
      </p>
    );
  }
  return (
    <div className="slo" data-testid="slo-panel" aria-label="Service level objectives">
      {slo.services.map((s) => (
        <div key={s.service} className="slo-row" data-testid="slo-row">
          <div className="slo-row__head">
            <span className="slo-row__name">{s.service}</span>
            <span
              className={s.meeting_slo ? "slo-badge slo-badge--ok" : "slo-badge slo-badge--bad"}
              data-testid="slo-status"
            >
              {s.meeting_slo ? "meeting" : "at risk"}
            </span>
          </div>
          <div className="slo-bar" role="progressbar" aria-valuenow={Math.round(s.budget_remaining * 100)} aria-valuemax={100}>
            <div
              className={`slo-bar__fill ${budgetClass(s.budget_remaining)}`}
              style={{ width: formatPercent(s.budget_remaining) }}
            />
          </div>
          <span className="slo-row__detail">
            {formatPercent(s.success_ratio)} success · target {formatPercent(s.target)} ·{" "}
            {formatPercent(s.budget_remaining)} budget left
          </span>
        </div>
      ))}
    </div>
  );
}
