import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReasoningTrace } from "../src/components/ReasoningTrace";
import type { QueryPlan, HealthFeatures } from "../src/lib/types";

function plan(overrides: Partial<QueryPlan> = {}): QueryPlan {
  return {
    original_query: "halal food open now",
    detected_language: "en",
    normalized_query: "halal food open now",
    semantic_text: "halal restaurants currently open",
    filters: { category: "restaurant", open_now: true, halal: true },
    top_k: 5,
    ...overrides,
  };
}

const allFeatures: HealthFeatures = {
  reranking: true,
  query_expansion: true,
  spell_correction: true,
};

describe("ReasoningTrace", () => {
  it("renders all seven pipeline steps", () => {
    render(<ReasoningTrace plan={plan()} resultCount={3} features={allFeatures} />);
    for (const key of ["detect", "normalize", "extract", "expand", "retrieve", "rerank", "answer"]) {
      expect(screen.getByTestId(`trace-step-${key}`)).toBeInTheDocument();
    }
  });

  it("shows the detected language and extracted filters", () => {
    render(<ReasoningTrace plan={plan()} resultCount={3} features={allFeatures} />);
    expect(screen.getByTestId("trace-step-detect")).toHaveTextContent("English");
    const extract = screen.getByTestId("trace-step-extract");
    expect(extract).toHaveTextContent(/Food/);
    expect(extract).toHaveTextContent(/open now/);
    expect(extract).toHaveTextContent(/halal/);
    expect(extract).toHaveClass("trace__step--active");
  });

  it("labels the normalize step as Translate for a non-English query", () => {
    const p = plan({
      detected_language: "fr",
      original_query: "ou est le stade",
      normalized_query: "where is the stadium",
      filters: { category: "stadium" },
    });
    render(<ReasoningTrace plan={p} resultCount={3} features={allFeatures} />);
    expect(screen.getByTestId("trace-step-normalize")).toHaveTextContent("Translate");
    expect(screen.getByTestId("trace-step-normalize")).toHaveTextContent("where is the stadium");
  });

  it("marks expand and rerank inactive when features are off", () => {
    const off: HealthFeatures = { reranking: false, query_expansion: false, spell_correction: false };
    render(<ReasoningTrace plan={plan({ filters: {} })} resultCount={0} features={off} />);
    expect(screen.getByTestId("trace-step-expand")).not.toHaveClass("trace__step--active");
    expect(screen.getByTestId("trace-step-rerank")).not.toHaveClass("trace__step--active");
    expect(screen.getByTestId("trace-step-rerank")).toHaveTextContent("score order");
    expect(screen.getByTestId("trace-step-extract")).toHaveTextContent("none");
    expect(screen.getByTestId("trace-step-answer")).not.toHaveClass("trace__step--active");
  });

  it("handles a null features prop and city/vegetarian/accessible filters", () => {
    const p = plan({
      filters: { city: "Toronto", vegetarian: true, wheelchair_accessible: true },
      normalized_query: "",
    });
    render(<ReasoningTrace plan={p} resultCount={2} features={null} />);
    const extract = screen.getByTestId("trace-step-extract");
    expect(extract).toHaveTextContent("Toronto");
    expect(extract).toHaveTextContent("vegetarian");
    expect(extract).toHaveTextContent("accessible");
    // empty normalized_query falls back to original_query
    expect(screen.getByTestId("trace-step-normalize")).toHaveTextContent("halal food open now");
  });
});
