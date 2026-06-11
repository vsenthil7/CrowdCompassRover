import type { ScoredEvent, VenueAvailability } from "../lib/types";
import { CATEGORY_META, formatDistance } from "../lib/display";
import { AvailabilityBadge } from "./AvailabilityBadge";

interface Props {
  hit: ScoredEvent;
  index: number;
  onRoute?: (hit: ScoredEvent) => void;
  availability?: VenueAvailability;
}

export function ResultRow({ hit, index, onRoute, availability }: Props) {
  const meta = CATEGORY_META[hit.event.category];
  const dist = formatDistance(hit.distance_km);
  return (
    <article className="row" style={{ animationDelay: `${index * 60}ms` }} data-testid="result-row">
      <div className="row__glyph" aria-hidden="true">
        {meta.glyph}
      </div>
      <div>
        <h3 className="row__name">{hit.event.name}</h3>
        <div className="row__meta">
          {meta.label} · {hit.event.city}
          {hit.event.halal ? " · Halal" : ""}
          {hit.event.vegetarian ? " · Vegetarian" : ""}
          {hit.event.wheelchair_accessible ? " · ♿" : ""}
        </div>
      </div>
      <div className="row__right">
        {availability ? (
          <AvailabilityBadge availability={availability} />
        ) : (
          <span className={`badge ${hit.event.open_now ? "badge--open" : "badge--closed"}`}>
            {hit.event.open_now ? "Open" : "Closed"}
          </span>
        )}
        {dist ? <span className="row__dist">{dist}</span> : null}
        {onRoute ? (
          <button
            className="row__route"
            onClick={() => onRoute(hit)}
            data-testid="route-button"
          >
            Route here
          </button>
        ) : null}
      </div>
    </article>
  );
}
