import type { HistoryEntry } from "../lib/types";
import { languageLabel } from "../lib/display";

interface Props {
  history: HistoryEntry[];
  onReplay: (query: string) => void;
}

export function HistoryPanel({ history, onReplay }: Props) {
  if (history.length === 0) {
    return null;
  }
  return (
    <section className="history" data-testid="history-panel">
      <h2 className="history__head">Conversation</h2>
      <ol className="history__list">
        {history.map((entry) => (
          <li key={entry.id} className="history__item">
            <button
              className="history__query"
              onClick={() => onReplay(entry.query)}
              data-testid="history-item"
            >
              {entry.query}
            </button>
            <span className="history__meta">
              {languageLabel(entry.language)} · {entry.resultCount} result
              {entry.resultCount === 1 ? "" : "s"}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
