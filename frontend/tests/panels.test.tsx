import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FeaturePanel } from "../src/components/FeaturePanel";
import { HistoryPanel } from "../src/components/HistoryPanel";
import { createSessionId, getSessionId, _resetSessionId } from "../src/lib/session";
import type { HealthStatus, HistoryEntry } from "../src/lib/types";

const health: HealthStatus = {
  status: "ok",
  mode: "mock",
  sessions_active: 3,
  features: { reranking: true, query_expansion: false, spell_correction: true },
};

describe("FeaturePanel", () => {
  it("renders feature pills with on/off state and session count", () => {
    render(<FeaturePanel health={health} />);
    expect(screen.getByTestId("feature-reranking")).toHaveClass("feature-pill--on");
    expect(screen.getByTestId("feature-query_expansion")).toHaveClass("feature-pill--off");
    expect(screen.getByTestId("sessions-active")).toHaveTextContent("3 active");
  });

  it("falls back to raw key label for unknown feature", () => {
    const custom: HealthStatus = {
      ...health,
      features: { ...health.features, mystery_flag: true } as never,
    };
    render(<FeaturePanel health={custom} />);
    expect(screen.getByTestId("feature-mystery_flag")).toHaveTextContent("mystery_flag");
  });
});

describe("HistoryPanel", () => {
  const entries: HistoryEntry[] = [
    { id: "1", query: "halal food", language: "en", resultCount: 3 },
    { id: "2", query: "estadio", language: "es", resultCount: 1 },
  ];

  it("renders nothing when empty", () => {
    const { container } = render(<HistoryPanel history={[]} onReplay={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders entries with singular/plural result labels", () => {
    render(<HistoryPanel history={entries} onReplay={() => {}} />);
    expect(screen.getByText(/3 results/)).toBeInTheDocument();
    expect(screen.getByText(/1 result$/)).toBeInTheDocument();
  });

  it("replays a query on click", () => {
    const onReplay = vi.fn();
    render(<HistoryPanel history={entries} onReplay={onReplay} />);
    fireEvent.click(screen.getAllByTestId("history-item")[0]);
    expect(onReplay).toHaveBeenCalledWith("halal food");
  });
});

describe("session id", () => {
  it("createSessionId is unique and prefixed", () => {
    const a = createSessionId();
    const b = createSessionId();
    expect(a).not.toBe(b);
    expect(a.startsWith("web-")).toBe(true);
  });

  it("getSessionId is stable until reset", () => {
    _resetSessionId();
    const first = getSessionId();
    expect(getSessionId()).toBe(first);
    _resetSessionId();
    expect(getSessionId()).not.toBe(first);
  });
});
