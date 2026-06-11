import type { OutboxStats } from "../lib/types";

interface Props {
  outbox: OutboxStats;
  onRelay: () => void;
  busy: boolean;
}

export function OutboxPanel({ outbox, onRelay, busy }: Props) {
  const { pending, delivered, failed, dead } = outbox.stats;
  return (
    <div className="outbox" data-testid="outbox-panel" aria-label="Event outbox">
      <div className="outbox__head">
        <h3 className="admin__subtitle">Event outbox</h3>
        <button
          className="btn btn--ghost"
          onClick={onRelay}
          disabled={busy}
          data-testid="outbox-relay"
        >
          {busy ? "Relaying…" : "Relay now"}
        </button>
      </div>
      <div className="outbox__stats">
        <span data-testid="outbox-pending">Pending {pending}</span>
        <span>Delivered {delivered}</span>
        <span>Failed {failed}</span>
        <span className={dead > 0 ? "outbox__dead" : ""}>Dead {dead}</span>
      </div>
      {outbox.dead_letters.length > 0 ? (
        <ul className="outbox__dead-list" data-testid="outbox-dead-list">
          {outbox.dead_letters.map((d) => (
            <li key={d.id} data-testid="outbox-dead-row">
              {d.topic} — {d.attempts} attempts{d.error ? `: ${d.error}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
