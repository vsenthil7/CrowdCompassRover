import type { SavedSearch } from "../lib/types";

interface Props {
  saved: SavedSearch[];
  currentQuery: string;
  onSave: () => void;
  onRun: (query: string) => void;
  onDelete: (id: string) => void;
  saving: boolean;
}

export function SavedSearches({
  saved,
  currentQuery,
  onSave,
  onRun,
  onDelete,
  saving,
}: Props) {
  return (
    <section className="saved" data-testid="saved-searches">
      <div className="saved__head">
        <h2 className="saved__title">Saved searches</h2>
        {currentQuery ? (
          <button
            className="btn btn--ghost"
            onClick={onSave}
            disabled={saving}
            data-testid="saved-add"
          >
            {saving ? "Saving…" : "Save current"}
          </button>
        ) : null}
      </div>
      {saved.length === 0 ? (
        <p className="saved__empty" data-testid="saved-empty">
          No saved searches yet.
        </p>
      ) : (
        <ul className="saved__list">
          {saved.map((s) => (
            <li key={s.id} className="saved__item">
              <button
                className="saved__run"
                onClick={() => onRun(s.query)}
                data-testid="saved-run"
              >
                {s.label}
              </button>
              <button
                className="saved__delete"
                onClick={() => onDelete(s.id)}
                aria-label={`Delete ${s.label}`}
                data-testid="saved-delete"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
