import type { FlagsReport } from "../lib/types";

interface Props {
  flags: FlagsReport;
}

/** Runtime feature flags as evaluated for the current context. Surfaces the
 *  backend /flags registry (rollout % + targeting evaluate to a boolean here). */
export function FlagsPanel({ flags }: Props) {
  const entries = Object.entries(flags.flags);
  if (entries.length === 0) {
    return (
      <p className="flags-empty" data-testid="flags-empty">
        No feature flags registered.
      </p>
    );
  }
  return (
    <ul className="flags" data-testid="flags-panel" aria-label="Feature flags">
      {entries.map(([key, enabled]) => (
        <li key={key} className="flags__row" data-testid={`flag-${key}`}>
          <span className="flags__key">{key}</span>
          <span
            className={enabled ? "flags__state flags__state--on" : "flags__state flags__state--off"}
            data-enabled={enabled ? "true" : "false"}
          >
            {enabled ? "on" : "off"}
          </span>
        </li>
      ))}
    </ul>
  );
}
