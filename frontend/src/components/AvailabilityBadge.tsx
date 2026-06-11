import type { VenueAvailability, OpenStateValue, CrowdValue } from "../lib/types";

interface Props {
  availability: VenueAvailability;
}

const OPEN_LABEL: Record<OpenStateValue, string> = {
  open: "Open",
  closed: "Closed",
  opening_soon: "Opening soon",
  closing_soon: "Closing soon",
};

const OPEN_CLASS: Record<OpenStateValue, string> = {
  open: "avail-badge--open",
  closed: "avail-badge--closed",
  opening_soon: "avail-badge--soon",
  closing_soon: "avail-badge--soon",
};

const CROWD_LABEL: Record<CrowdValue, string> = {
  quiet: "Quiet",
  moderate: "Moderate",
  busy: "Busy",
  packed: "Packed",
  unknown: "",
};

const CROWD_CLASS: Record<CrowdValue, string> = {
  quiet: "crowd--quiet",
  moderate: "crowd--moderate",
  busy: "crowd--busy",
  packed: "crowd--packed",
  unknown: "",
};

/** Compact live status: open-state (with closing/opening countdown), a transient-closure
 *  flag, the crowd level, and any reported wait. Designed to sit in a search ResultRow. */
export function AvailabilityBadge({ availability: a }: Props) {
  // A trusted transient closure overrides the schedule label.
  const stateLabel = a.temporarily_closed ? "Temporarily closed" : OPEN_LABEL[a.open_state];
  const stateClass = a.temporarily_closed ? "avail-badge--closed" : OPEN_CLASS[a.open_state];
  const showCountdown =
    !a.temporarily_closed &&
    a.minutes_to_transition != null &&
    (a.open_state === "closing_soon" || a.open_state === "opening_soon");

  return (
    <span className="avail" data-testid="availability-badge" data-state={a.open_state}>
      <span className={`avail-badge ${stateClass}`} data-testid="avail-state">
        {stateLabel}
        {showCountdown ? ` · ${a.minutes_to_transition}m` : ""}
      </span>
      {a.crowd !== "unknown" ? (
        <span className={`crowd ${CROWD_CLASS[a.crowd]}`} data-testid="avail-crowd">
          {CROWD_LABEL[a.crowd]}
          {a.wait_minutes != null ? ` · ${a.wait_minutes}m wait` : ""}
        </span>
      ) : null}
    </span>
  );
}
