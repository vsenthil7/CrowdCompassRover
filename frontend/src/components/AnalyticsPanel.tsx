import type { AnalyticsSnapshot } from "../lib/types";
import { formatPercent } from "../lib/a11y";

interface Props {
  analytics: AnalyticsSnapshot;
}

/** Query analytics: volume, zero-result rate, and breakdowns by language and
 *  category, plus the top queries. Surfaces the backend /analytics recorder
 *  that previously had no UI. */
export function AnalyticsPanel({ analytics }: Props) {
  const { total, zero_result, zero_result_rate, by_language, by_category, top_queries } = analytics;
  if (total === 0) {
    return (
      <p className="analytics-empty" data-testid="analytics-empty">
        No queries recorded yet — run a few searches.
      </p>
    );
  }
  return (
    <div className="analytics" data-testid="analytics-panel" aria-label="Query analytics">
      <div className="analytics__stats" data-testid="analytics-stats">
        <span data-testid="analytics-total">Total {total}</span>
        <span>Zero-result {zero_result}</span>
        <span className={zero_result_rate > 0.2 ? "analytics__warn" : ""}>
          Zero-rate {formatPercent(zero_result_rate)}
        </span>
      </div>

      <Breakdown title="By language" data={by_language} testid="analytics-by-language" />
      <Breakdown title="By category" data={by_category} testid="analytics-by-category" />

      {top_queries.length > 0 ? (
        <div className="analytics__top" data-testid="analytics-top">
          <div className="analytics__sub">Top queries</div>
          <ol className="analytics__list">
            {top_queries.map(([q, n]) => (
              <li key={q} data-testid="analytics-top-row">
                <span className="analytics__q">{q}</span>
                <span className="analytics__n">{n}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}

function Breakdown({
  title,
  data,
  testid,
}: {
  title: string;
  data: Record<string, number>;
  testid: string;
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) return null;
  return (
    <div className="analytics__breakdown" data-testid={testid}>
      <div className="analytics__sub">{title}</div>
      <div className="analytics__chips">
        {entries.map(([k, v]) => (
          <span key={k} className="analytics__chip">
            {k} <strong>{v}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}
