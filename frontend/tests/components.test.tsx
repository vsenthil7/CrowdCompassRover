import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ResultRow } from "../src/components/ResultRow";
import { PlanStrip } from "../src/components/PlanStrip";
import { AnswerCard } from "../src/components/AnswerCard";
import { SearchControls } from "../src/components/SearchControls";
import type { ChatAnswer, QueryPlan, ScoredEvent } from "../src/lib/types";

function makeHit(over: Partial<ScoredEvent["event"]> = {}, dist: number | null = null): ScoredEvent {
  return {
    score: 0.9,
    distance_km: dist,
    event: {
      id: "e1",
      name: "Test Stadium",
      category: "stadium",
      city: "New York",
      description: "d",
      languages: ["en"],
      location: { lat: 0, lon: 0 },
      open_now: true,
      tags: [],
      halal: false,
      vegetarian: false,
      wheelchair_accessible: false,
      capacity: null,
      ...over,
    },
  };
}

describe("ResultRow", () => {
  it("renders name, category and open badge", () => {
    render(<ResultRow hit={makeHit()} index={0} />);
    expect(screen.getByText("Test Stadium")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();
  });

  it("renders closed badge, distance and dietary flags", () => {
    const hit = makeHit({ open_now: false, halal: true, vegetarian: true, wheelchair_accessible: true, category: "restaurant" }, 2.5);
    render(<ResultRow hit={hit} index={1} />);
    expect(screen.getByText("Closed")).toBeInTheDocument();
    expect(screen.getByText("2.5 km")).toBeInTheDocument();
    expect(screen.getByText(/Halal/)).toBeInTheDocument();
  });
});

describe("PlanStrip", () => {
  function plan(over: Partial<QueryPlan> = {}): QueryPlan {
    return {
      original_query: "q",
      detected_language: "es",
      normalized_query: "food",
      semantic_text: "food",
      filters: {},
      top_k: 5,
      ...over,
    };
  }

  it("shows language and 'none' when no filters", () => {
    render(<PlanStrip plan={plan()} />);
    expect(screen.getByText("Español")).toBeInTheDocument();
    expect(screen.getByText("none")).toBeInTheDocument();
  });

  it("lists all active filters", () => {
    render(
      <PlanStrip
        plan={plan({
          filters: {
            city: "New York",
            category: "restaurant",
            open_now: true,
            halal: true,
            vegetarian: true,
            wheelchair_accessible: true,
          },
        })}
      />,
    );
    expect(screen.getByText(/New York, Food, Open now, Halal, Vegetarian, Accessible/)).toBeInTheDocument();
  });

  it("renders dash when normalized query empty", () => {
    render(<PlanStrip plan={plan({ normalized_query: "" })} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});

describe("AnswerCard", () => {
  it("renders answer text and language", () => {
    const ans: ChatAnswer = { answer: "Go here", language: "fr", citations: [], results: [] };
    render(<AnswerCard answer={ans} />);
    expect(screen.getByText("Go here")).toBeInTheDocument();
    expect(screen.getByText(/Français/)).toBeInTheDocument();
  });
});

describe("SearchControls", () => {
  const base = {
    query: "",
    onQueryChange: vi.fn(),
    onSubmit: vi.fn(),
    useLocation: false,
    onToggleLocation: vi.fn(),
    loading: false,
    examples: ["halal food"],
    onExample: vi.fn(),
  };

  it("calls onQueryChange when typing", () => {
    const onQueryChange = vi.fn();
    render(<SearchControls {...base} onQueryChange={onQueryChange} />);
    fireEvent.change(screen.getByLabelText("Ask in any language"), { target: { value: "x" } });
    expect(onQueryChange).toHaveBeenCalledWith("x");
  });

  it("disables button when query empty", () => {
    render(<SearchControls {...base} query="" />);
    expect(screen.getByText("Ask")).toBeDisabled();
  });

  it("submits on click", () => {
    const onSubmit = vi.fn();
    render(<SearchControls {...base} query="hi" onSubmit={onSubmit} />);
    fireEvent.click(screen.getByText("Ask"));
    expect(onSubmit).toHaveBeenCalled();
  });

  it("submits on Enter key", () => {
    const onSubmit = vi.fn();
    render(<SearchControls {...base} query="hi" onSubmit={onSubmit} />);
    fireEvent.keyDown(screen.getByLabelText("Ask in any language"), { key: "Enter" });
    expect(onSubmit).toHaveBeenCalled();
  });

  it("does not submit on other keys", () => {
    const onSubmit = vi.fn();
    render(<SearchControls {...base} query="hi" onSubmit={onSubmit} />);
    fireEvent.keyDown(screen.getByLabelText("Ask in any language"), { key: "a" });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows spinner when loading", () => {
    render(<SearchControls {...base} query="hi" loading={true} />);
    expect(screen.getByTestId("spinner")).toBeInTheDocument();
  });

  it("toggles location", () => {
    const onToggleLocation = vi.fn();
    render(<SearchControls {...base} onToggleLocation={onToggleLocation} />);
    fireEvent.click(screen.getByRole("checkbox"));
    expect(onToggleLocation).toHaveBeenCalledWith(true);
  });

  it("fires example click", () => {
    const onExample = vi.fn();
    render(<SearchControls {...base} onExample={onExample} />);
    fireEvent.click(screen.getByText("halal food"));
    expect(onExample).toHaveBeenCalledWith("halal food");
  });
});
