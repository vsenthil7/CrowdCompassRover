import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, renderHook, waitFor, act } from "@testing-library/react";
import { AvailabilityBadge } from "../src/components/AvailabilityBadge";
import { ResultRow } from "../src/components/ResultRow";
import { useAvailability } from "../src/hooks/useAvailability";
import type { VenueAvailability, ScoredEvent } from "../src/lib/types";

vi.mock("../src/lib/api");
import * as api from "../src/lib/api";
const mockedApi = api as unknown as Record<string, ReturnType<typeof vi.fn>>;

function avail(overrides: Partial<VenueAvailability> = {}): VenueAvailability {
  return {
    venue_id: "v1",
    open_state: "open",
    is_open: true,
    effectively_open: true,
    minutes_to_transition: null,
    crowd: "unknown",
    wait_minutes: null,
    temporarily_closed: false,
    note: "",
    ...overrides,
  };
}

describe("AvailabilityBadge", () => {
  it("renders open with no crowd chip when crowd unknown", () => {
    render(<AvailabilityBadge availability={avail()} />);
    expect(screen.getByTestId("avail-state")).toHaveTextContent("Open");
    expect(screen.queryByTestId("avail-crowd")).toBeNull();
  });

  it("renders closed", () => {
    render(<AvailabilityBadge availability={avail({ open_state: "closed", is_open: false, effectively_open: false })} />);
    expect(screen.getByTestId("avail-state")).toHaveTextContent("Closed");
  });

  it("shows a closing-soon countdown", () => {
    render(<AvailabilityBadge availability={avail({ open_state: "closing_soon", minutes_to_transition: 15 })} />);
    expect(screen.getByTestId("avail-state")).toHaveTextContent("Closing soon · 15m");
  });

  it("shows an opening-soon countdown", () => {
    render(<AvailabilityBadge availability={avail({ open_state: "opening_soon", is_open: false, minutes_to_transition: 10 })} />);
    expect(screen.getByTestId("avail-state")).toHaveTextContent("Opening soon · 10m");
  });

  it("overrides the label when temporarily closed", () => {
    render(
      <AvailabilityBadge
        availability={avail({ open_state: "open", temporarily_closed: true, effectively_open: false, note: "incident" })}
      />,
    );
    expect(screen.getByTestId("avail-state")).toHaveTextContent("Temporarily closed");
  });

  it("renders crowd level and wait when present", () => {
    render(<AvailabilityBadge availability={avail({ crowd: "packed", wait_minutes: 40 })} />);
    expect(screen.getByTestId("avail-crowd")).toHaveTextContent("Packed · 40m wait");
  });

  it("renders crowd without wait", () => {
    render(<AvailabilityBadge availability={avail({ crowd: "busy" })} />);
    expect(screen.getByTestId("avail-crowd")).toHaveTextContent("Busy");
  });

  it("does not show a countdown when open (not soon)", () => {
    render(<AvailabilityBadge availability={avail({ open_state: "open", minutes_to_transition: 200 })} />);
    expect(screen.getByTestId("avail-state").textContent).toBe("Open");
  });
});

describe("ResultRow with availability", () => {
  const hit: ScoredEvent = {
    event: {
      id: "v1", name: "Halal Cart", category: "restaurant", city: "NYC",
      description: "", languages: [], location: { lat: 40, lon: -73 },
      open_now: true, tags: [], halal: true, vegetarian: false,
      wheelchair_accessible: false, capacity: null,
    },
    score: 1, distance_km: 0.5,
  };

  it("shows the live availability badge when provided (not the static one)", () => {
    render(<ResultRow hit={hit} index={0} availability={avail({ crowd: "busy" })} />);
    expect(screen.getByTestId("availability-badge")).toBeInTheDocument();
    expect(screen.getByTestId("avail-crowd")).toHaveTextContent("Busy");
  });

  it("falls back to the static open/closed badge without availability", () => {
    render(<ResultRow hit={hit} index={0} />);
    expect(screen.queryByTestId("availability-badge")).toBeNull();
    expect(screen.getByText("Open")).toBeInTheDocument();
  });
});

describe("useAvailability hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns an empty map for no venue ids", async () => {
    const { result } = renderHook(() => useAvailability([]));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.availability).toEqual({});
  });

  it("fetches availability for each venue id", async () => {
    mockedApi.availability = vi.fn(async (id: string) => avail({ venue_id: id, crowd: "quiet" }));
    const { result } = renderHook(() => useAvailability(["a", "b"]));
    await waitFor(() => expect(Object.keys(result.current.availability)).toHaveLength(2));
    expect(result.current.availability.a.crowd).toBe("quiet");
    expect(mockedApi.availability).toHaveBeenCalledTimes(2);
  });

  it("swallows per-venue failures without blanking others", async () => {
    mockedApi.availability = vi.fn(async (id: string) => {
      if (id === "bad") throw new Error("boom");
      return avail({ venue_id: id });
    });
    const { result } = renderHook(() => useAvailability(["good", "bad"]));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.availability.good).toBeTruthy();
    expect(result.current.availability.bad).toBeUndefined();
  });

  it("passes the optional 'at' time through", async () => {
    mockedApi.availability = vi.fn(async (id: string) => avail({ venue_id: id }));
    renderHook(() => useAvailability(["a"], "2026-06-02T20:00:00Z"));
    await waitFor(() => expect(mockedApi.availability).toHaveBeenCalledWith("a", "2026-06-02T20:00:00Z"));
  });

  it("reload re-fetches", async () => {
    mockedApi.availability = vi.fn(async (id: string) => avail({ venue_id: id }));
    const { result } = renderHook(() => useAvailability(["a"]));
    await waitFor(() => expect(result.current.availability.a).toBeTruthy());
    await act(async () => {
      await result.current.reload();
    });
    expect(mockedApi.availability).toHaveBeenCalledTimes(2);
  });
});
