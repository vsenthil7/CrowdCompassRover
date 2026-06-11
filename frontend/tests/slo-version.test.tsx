import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SloPanel } from "../src/components/SloPanel";
import { VersionBadge } from "../src/components/VersionBadge";
import type { SloReport } from "../src/lib/types";

function svc(overrides: Partial<SloReport["services"][0]>) {
  return {
    service: "search",
    target: 0.99,
    total: 100,
    success_ratio: 1,
    meeting_slo: true,
    budget_remaining: 1,
    ...overrides,
  };
}

describe("SloPanel", () => {
  it("shows empty state with no services", () => {
    render(<SloPanel slo={{ services: [] }} />);
    expect(screen.getByTestId("slo-empty")).toBeInTheDocument();
  });

  it("renders an ok service", () => {
    render(<SloPanel slo={{ services: [svc({ budget_remaining: 1, meeting_slo: true })] }} />);
    expect(screen.getByTestId("slo-row")).toBeInTheDocument();
    expect(screen.getByTestId("slo-status")).toHaveTextContent("meeting");
    expect(document.querySelector(".slo-bar__fill--ok")).toBeTruthy();
  });

  it("renders a warning service (budget < 50%)", () => {
    render(<SloPanel slo={{ services: [svc({ budget_remaining: 0.3 })] }} />);
    expect(document.querySelector(".slo-bar__fill--warning")).toBeTruthy();
  });

  it("renders a critical service (budget exhausted)", () => {
    render(
      <SloPanel slo={{ services: [svc({ budget_remaining: 0, meeting_slo: false, success_ratio: 0.8 })] }} />,
    );
    expect(screen.getByTestId("slo-status")).toHaveTextContent("at risk");
    expect(document.querySelector(".slo-bar__fill--critical")).toBeTruthy();
  });

  it("renders multiple services", () => {
    render(
      <SloPanel
        slo={{ services: [svc({ service: "search" }), svc({ service: "chat" })] }}
      />,
    );
    expect(screen.getAllByTestId("slo-row")).toHaveLength(2);
  });
});

describe("VersionBadge", () => {
  it("shows the current version", () => {
    render(<VersionBadge version={{ current: "v2", supported: ["v1", "v2"] }} />);
    const badge = screen.getByTestId("version-badge");
    expect(badge).toHaveTextContent("API v2");
    expect(badge).toHaveAttribute("title", "Supported: v1, v2");
  });
});
