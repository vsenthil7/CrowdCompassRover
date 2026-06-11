import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RoutePanel } from "../src/components/RoutePanel";
import { ErrorBoundary } from "../src/components/ErrorBoundary";
import { ResultRow } from "../src/components/ResultRow";
import type { RouteResponse, ScoredEvent } from "../src/lib/types";

const routeResponse: RouteResponse = {
  options: [
    { mode: "walk", total_distance_km: 5, total_duration_min: 60, estimated_cost: 0, currency: "USD", legs: [] },
    { mode: "transit", total_distance_km: 6, total_duration_min: 25, estimated_cost: 2.5, currency: "USD", legs: [] },
    { mode: "drive", total_distance_km: 6.5, total_duration_min: 15, estimated_cost: 9, currency: "USD", legs: [] },
  ],
  cheapest: { mode: "walk", total_distance_km: 5, total_duration_min: 60, estimated_cost: 0, currency: "USD", legs: [] },
  fastest: { mode: "drive", total_distance_km: 6.5, total_duration_min: 15, estimated_cost: 9, currency: "USD", legs: [] },
};

describe("RoutePanel", () => {
  it("renders options with cheapest and fastest badges", () => {
    render(<RoutePanel routes={routeResponse} destinationName="MetLife Stadium" onClose={() => {}} />);
    expect(screen.getByText(/Routes to MetLife Stadium/)).toBeInTheDocument();
    expect(screen.getAllByTestId("route-option")).toHaveLength(3);
    expect(screen.getByText("Cheapest")).toBeInTheDocument();
    expect(screen.getByText("Fastest")).toBeInTheDocument();
    expect(screen.getByText("Free")).toBeInTheDocument();
  });

  it("calls onClose", () => {
    const onClose = vi.fn();
    render(<RoutePanel routes={routeResponse} destinationName="X" onClose={onClose} />);
    fireEvent.click(screen.getByTestId("route-close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("renders without badges when no cheapest/fastest", () => {
    const empty: RouteResponse = { options: [], cheapest: null, fastest: null };
    render(<RoutePanel routes={empty} destinationName="Y" onClose={() => {}} />);
    expect(screen.queryAllByTestId("route-option")).toHaveLength(0);
  });

  it("renders fallback glyph for unknown travel mode", () => {
    const odd: RouteResponse = {
      options: [
        {
          mode: "teleport" as never,
          total_distance_km: 1,
          total_duration_min: 1,
          estimated_cost: 0,
          currency: "USD",
          legs: [],
        },
      ],
      cheapest: null,
      fastest: null,
    };
    render(<RoutePanel routes={odd} destinationName="Z" onClose={() => {}} />);
    expect(screen.getByTestId("route-option")).toHaveTextContent("·");
  });
});

describe("ErrorBoundary", () => {
  function Boom(): JSX.Element {
    throw new Error("kaboom");
  }

  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">ok</div>
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("renders fallback message on error and recovers", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("error-boundary")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("error-reset"));
    spy.mockRestore();
  });

  it("renders custom fallback when provided", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">nope</div>}>
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
    spy.mockRestore();
  });
});

describe("ResultRow route button", () => {
  const hit: ScoredEvent = {
    score: 0.9,
    distance_km: null,
    event: {
      id: "e1",
      name: "Stadium",
      category: "stadium",
      city: "NYC",
      description: "d",
      languages: [],
      location: { lat: 0, lon: 0 },
      open_now: true,
      tags: [],
      halal: false,
      vegetarian: false,
      wheelchair_accessible: false,
      capacity: null,
    },
  };

  it("shows route button when onRoute provided and fires it", () => {
    const onRoute = vi.fn();
    render(<ResultRow hit={hit} index={0} onRoute={onRoute} />);
    fireEvent.click(screen.getByTestId("route-button"));
    expect(onRoute).toHaveBeenCalledWith(hit);
  });

  it("hides route button when onRoute absent", () => {
    render(<ResultRow hit={hit} index={0} />);
    expect(screen.queryByTestId("route-button")).toBeNull();
  });
});
