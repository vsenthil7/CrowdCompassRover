import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalyticsPanel } from "../src/components/AnalyticsPanel";
import { HealthPanel } from "../src/components/HealthPanel";
import { FlagsPanel } from "../src/components/FlagsPanel";
import { TracesPanel } from "../src/components/TracesPanel";
import { BulkheadPanel } from "../src/components/BulkheadPanel";
import type {
  AnalyticsSnapshot,
  ReadinessReport,
  TracesReport,
  BulkheadStats,
} from "../src/lib/types";

describe("AnalyticsPanel", () => {
  it("shows empty state when no queries recorded", () => {
    const a: AnalyticsSnapshot = {
      total: 0, zero_result: 0, zero_result_rate: 0,
      by_language: {}, by_category: {}, top_queries: [],
    };
    render(<AnalyticsPanel analytics={a} />);
    expect(screen.getByTestId("analytics-empty")).toBeInTheDocument();
  });

  it("renders stats, breakdowns and top queries", () => {
    const a: AnalyticsSnapshot = {
      total: 42, zero_result: 3, zero_result_rate: 0.07,
      by_language: { en: 30, es: 12 },
      by_category: { restaurant: 20, stadium: 22 },
      top_queries: [["halal food", 9], ["stadium route", 7]],
    };
    render(<AnalyticsPanel analytics={a} />);
    expect(screen.getByTestId("analytics-total")).toHaveTextContent("42");
    expect(screen.getByTestId("analytics-by-language")).toBeInTheDocument();
    expect(screen.getByTestId("analytics-by-category")).toBeInTheDocument();
    expect(screen.getAllByTestId("analytics-top-row")).toHaveLength(2);
  });

  it("flags a high zero-result rate", () => {
    const a: AnalyticsSnapshot = {
      total: 10, zero_result: 5, zero_result_rate: 0.5,
      by_language: { en: 10 }, by_category: {}, top_queries: [],
    };
    render(<AnalyticsPanel analytics={a} />);
    expect(document.querySelector(".analytics__warn")).toBeTruthy();
  });

  it("omits breakdowns and top list when empty", () => {
    const a: AnalyticsSnapshot = {
      total: 5, zero_result: 0, zero_result_rate: 0,
      by_language: {}, by_category: {}, top_queries: [],
    };
    render(<AnalyticsPanel analytics={a} />);
    expect(screen.queryByTestId("analytics-by-language")).toBeNull();
    expect(screen.queryByTestId("analytics-top")).toBeNull();
  });
});

describe("HealthPanel", () => {
  it("renders ready with component rows", () => {
    const r: ReadinessReport = {
      state: "ready", ready: true,
      components: [
        { name: "elastic", state: "healthy", detail: "ok", latency_ms: 12.3 },
        { name: "gemini", state: "healthy", detail: "", latency_ms: 4 },
      ],
    };
    render(<HealthPanel readiness={r} />);
    expect(screen.getByTestId("health-overall")).toHaveTextContent("READY");
    expect(screen.getByTestId("health-row-elastic")).toBeInTheDocument();
    expect(document.querySelectorAll(".health__dot--ok").length).toBe(2);
  });

  it("renders not-ready with a degraded component", () => {
    const r: ReadinessReport = {
      state: "degraded", ready: false,
      components: [{ name: "elastic", state: "unhealthy", detail: "timeout", latency_ms: 99 }],
    };
    render(<HealthPanel readiness={r} />);
    expect(screen.getByTestId("health-overall")).toHaveTextContent("NOT READY");
    expect(document.querySelector(".health__dot--bad")).toBeTruthy();
  });

  it("shows empty state with no checks", () => {
    const r: ReadinessReport = { state: "ready", ready: true, components: [] };
    render(<HealthPanel readiness={r} />);
    expect(screen.getByTestId("health-empty")).toBeInTheDocument();
  });
});

describe("FlagsPanel", () => {
  it("renders on/off flags", () => {
    render(<FlagsPanel flags={{ flags: { new_ranker: true, beta_ui: false } }} />);
    expect(screen.getByTestId("flag-new_ranker")).toHaveTextContent("on");
    expect(screen.getByTestId("flag-beta_ui")).toHaveTextContent("off");
  });

  it("shows empty state with no flags", () => {
    render(<FlagsPanel flags={{ flags: {} }} />);
    expect(screen.getByTestId("flags-empty")).toBeInTheDocument();
  });
});

describe("TracesPanel", () => {
  it("shows empty state when no spans", () => {
    render(<TracesPanel traces={{ spans: [] }} />);
    expect(screen.getByTestId("traces-empty")).toBeInTheDocument();
  });

  it("renders spans and indents children under parents", () => {
    const t: TracesReport = {
      spans: [
        { trace_id: "t1", span_id: "root", parent_id: null, name: "search", duration_ms: 12.5, status: "ok", attributes: {} },
        { trace_id: "t1", span_id: "child", parent_id: "root", name: "retrieve", duration_ms: 8.2, status: "ok", attributes: {} },
        { trace_id: "t1", span_id: "err", parent_id: "root", name: "ground", duration_ms: 1.1, status: "error", attributes: {} },
      ],
    };
    render(<TracesPanel traces={t} />);
    const rows = screen.getAllByTestId("trace-row");
    expect(rows).toHaveLength(3);
    expect(document.querySelector(".traces__status--err")).toBeTruthy();
    // The child row is indented (paddingLeft > 0).
    const childRow = rows.find((r) => r.textContent?.includes("retrieve"))!;
    expect(childRow.getAttribute("style")).toContain("padding-left");
  });

  it("tolerates an orphan parent reference without infinite recursion", () => {
    const t: TracesReport = {
      spans: [
        { trace_id: "t1", span_id: "a", parent_id: "missing", name: "x", duration_ms: 1, status: "ok", attributes: {} },
      ],
    };
    render(<TracesPanel traces={t} />);
    expect(screen.getAllByTestId("trace-row")).toHaveLength(1);
  });

  it("breaks out of a cyclic parent chain via the recursion guard", () => {
    // Malformed data: a <-> b cycle. The depth() guard must stop, not hang.
    const t: TracesReport = {
      spans: [
        { trace_id: "t1", span_id: "a", parent_id: "b", name: "a", duration_ms: 1, status: "ok", attributes: {} },
        { trace_id: "t1", span_id: "b", parent_id: "a", name: "b", duration_ms: 1, status: "ok", attributes: {} },
      ],
    };
    render(<TracesPanel traces={t} />);
    expect(screen.getAllByTestId("trace-row")).toHaveLength(2);
  });
});

describe("BulkheadPanel", () => {
  function bh(overrides: Partial<BulkheadStats>): BulkheadStats {
    return { name: "search", max_concurrent: 16, active: 0, queued: 0, rejected: 0, ...overrides };
  }

  it("renders ok utilisation", () => {
    render(<BulkheadPanel bulkhead={bh({ active: 2 })} />);
    expect(screen.getByTestId("bulkhead-active")).toHaveTextContent("2/16 active");
    expect(document.querySelector(".bulkhead-bar__fill--ok")).toBeTruthy();
  });

  it("renders warning utilisation (>=70%)", () => {
    render(<BulkheadPanel bulkhead={bh({ active: 12 })} />);
    expect(document.querySelector(".bulkhead-bar__fill--warning")).toBeTruthy();
  });

  it("renders critical utilisation (saturated)", () => {
    render(<BulkheadPanel bulkhead={bh({ active: 16, queued: 4, rejected: 2 })} />);
    expect(document.querySelector(".bulkhead-bar__fill--critical")).toBeTruthy();
    expect(screen.getByTestId("bulkhead-panel")).toHaveTextContent("4 queued");
    expect(screen.getByTestId("bulkhead-panel")).toHaveTextContent("2 rejected");
  });

  it("handles zero capacity without dividing by zero", () => {
    render(<BulkheadPanel bulkhead={bh({ max_concurrent: 0, active: 0, rejected: undefined })} />);
    expect(screen.getByTestId("bulkhead-panel")).toBeInTheDocument();
  });
});
