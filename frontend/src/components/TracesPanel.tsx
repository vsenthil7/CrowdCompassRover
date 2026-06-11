import type { TracesReport } from "../lib/types";

interface Props {
  traces: TracesReport;
}

/** Recent distributed-tracing spans (most recent first). Indents child spans
 *  under their parent so a request's plan→search→ground tree is legible.
 *  Surfaces the backend /traces exporter that previously had no UI. */
export function TracesPanel({ traces }: Props) {
  const { spans } = traces;
  if (spans.length === 0) {
    return (
      <p className="traces-empty" data-testid="traces-empty">
        No traces captured yet — run a search or chat.
      </p>
    );
  }
  // Depth = how many ancestors a span has within the returned set.
  const byId = new Map(spans.map((s) => [s.span_id, s]));
  const depth = (id: string | null, guard = 0): number => {
    if (!id || guard > 20) return 0;
    const s = byId.get(id);
    if (!s || !s.parent_id) return 0;
    return 1 + depth(s.parent_id, guard + 1);
  };

  return (
    <div className="traces" data-testid="traces-panel" aria-label="Recent traces">
      {spans.map((s) => (
        <div
          key={s.span_id}
          className="traces__row"
          data-testid="trace-row"
          style={{ paddingLeft: `${depth(s.span_id) * 16}px` }}
        >
          <span
            className={s.status === "ok" ? "traces__status traces__status--ok" : "traces__status traces__status--err"}
            aria-hidden="true"
          />
          <span className="traces__name">{s.name}</span>
          <span className="traces__dur">{s.duration_ms.toFixed(2)} ms</span>
        </div>
      ))}
    </div>
  );
}
