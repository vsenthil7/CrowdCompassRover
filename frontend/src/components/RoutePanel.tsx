import type { RouteOption, RouteResponse } from "../lib/types";
import {
  TRAVEL_MODE_META,
  formatCost,
  formatDistance,
  formatDuration,
  travelModeLabel,
} from "../lib/display";

interface Props {
  routes: RouteResponse;
  destinationName: string;
  onClose: () => void;
}

function OptionRow({
  option,
  badge,
}: {
  option: RouteOption;
  badge: string | null;
}) {
  const meta = TRAVEL_MODE_META[option.mode];
  return (
    <div className="route-option" data-testid="route-option">
      <span className="route-option__glyph">{meta?.glyph ?? "·"}</span>
      <span className="route-option__mode">{travelModeLabel(option.mode)}</span>
      <span className="route-option__detail">
        {formatDuration(option.total_duration_min)} · {formatDistance(option.total_distance_km)}
      </span>
      <span className="route-option__cost">
        {formatCost(option.estimated_cost, option.currency)}
      </span>
      {badge ? <span className="route-option__badge">{badge}</span> : null}
    </div>
  );
}

export function RoutePanel({ routes, destinationName, onClose }: Props) {
  const cheapestMode = routes.cheapest?.mode;
  const fastestMode = routes.fastest?.mode;

  return (
    <section className="route-panel" data-testid="route-panel">
      <div className="route-panel__head">
        <h2 className="route-panel__title">Routes to {destinationName}</h2>
        <button className="route-panel__close" onClick={onClose} data-testid="route-close">
          ✕
        </button>
      </div>
      <div className="route-panel__list">
        {routes.options.map((option) => {
          let badge: string | null = null;
          if (option.mode === cheapestMode) badge = "Cheapest";
          else if (option.mode === fastestMode) badge = "Fastest";
          return <OptionRow key={option.mode} option={option} badge={badge} />;
        })}
      </div>
    </section>
  );
}
