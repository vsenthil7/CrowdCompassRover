interface Props {
  total: number | null;
  shown: number;
  hasMore: boolean;
  loading: boolean;
  onNext: () => void;
}

export function Pagination({ total, shown, hasMore, loading, onNext }: Props) {
  if (total === null) {
    return null;
  }
  return (
    <div className="pagination" data-testid="pagination">
      <span className="pagination__count">
        Showing {shown} of {total}
      </span>
      {hasMore ? (
        <button
          className="btn btn--ghost"
          onClick={onNext}
          disabled={loading}
          data-testid="pagination-next"
        >
          {loading ? "Loading…" : "Show more"}
        </button>
      ) : (
        <span className="pagination__end" data-testid="pagination-end">
          End of results
        </span>
      )}
    </div>
  );
}
