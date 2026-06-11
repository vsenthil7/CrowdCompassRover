interface Props {
  query: string;
  onQueryChange: (q: string) => void;
  onSubmit: () => void;
  useLocation: boolean;
  onToggleLocation: (v: boolean) => void;
  loading: boolean;
  examples: string[];
  onExample: (q: string) => void;
}

export function SearchControls({
  query,
  onQueryChange,
  onSubmit,
  useLocation,
  onToggleLocation,
  loading,
  examples,
  onExample,
}: Props) {
  return (
    <div role="search" aria-label="Venue and event search">
      <div className="searchbar">
        <input
          aria-label="Ask in any language"
          placeholder="Ask in any language — e.g. dónde comer halal cerca ahora"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSubmit();
          }}
        />
        <button className="btn btn--go" onClick={onSubmit} disabled={loading || !query.trim()}>
          {loading ? <span className="spinner" data-testid="spinner" /> : "Ask"}
        </button>
      </div>
      <div className="controls">
        <label className="toggle">
          <input
            type="checkbox"
            checked={useLocation}
            onChange={(e) => onToggleLocation(e.target.checked)}
          />
          Use my stadium location
        </label>
        <div className="chips">
          {examples.map((ex) => (
            <button key={ex} className="chip" onClick={() => onExample(ex)}>
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
