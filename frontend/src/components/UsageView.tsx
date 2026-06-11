import type { UsageInfo } from "../lib/types";
import { formatPercent } from "../lib/a11y";

interface Props {
  usage: UsageInfo;
}

export function UsageView({ usage }: Props) {
  const used = usage.quota > 0 ? usage.count / usage.quota : 0;
  return (
    <section className="usage" data-testid="usage-view" aria-label="Usage and quota">
      <h3 className="usage__title">Usage · {usage.period}</h3>
      <div className="usage__bar" role="progressbar" aria-valuenow={usage.count} aria-valuemax={usage.quota}>
        <div className="usage__fill" style={{ width: formatPercent(used) }} />
      </div>
      <p className="usage__line">
        {usage.count} of {usage.quota} used · {usage.remaining} remaining
      </p>
      {Object.keys(usage.by_action).length > 0 ? (
        <ul className="usage__actions">
          {Object.entries(usage.by_action).map(([action, n]) => (
            <li key={action} data-testid="usage-action">
              {action}: {n}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
