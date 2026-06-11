import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { App } from "../src/App";
import { useRover, DEFAULT_LOCATION } from "../src/hooks/useRover";
import * as api from "../src/lib/api";
import type { ChatAnswer, SearchResponse } from "../src/lib/types";

vi.mock("../src/lib/api");

const mockedApi = vi.mocked(api);

const searchRes: SearchResponse = {
  plan: {
    original_query: "halal food open now",
    detected_language: "en",
    normalized_query: "halal food open now",
    semantic_text: "halal food open now",
    filters: { halal: true, open_now: true },
    top_k: 5,
  },
  results: [
    {
      score: 0.9,
      distance_km: 1.2,
      event: {
        id: "e1",
        name: "Halal Guys",
        category: "restaurant",
        city: "New York",
        description: "d",
        languages: ["en"],
        location: { lat: 40.8, lon: -74.0 },
        open_now: true,
        tags: [],
        halal: true,
        vegetarian: false,
        wheelchair_accessible: false,
        capacity: null,
      },
    },
  ],
};

const chatRes: ChatAnswer = {
  answer: "Try Halal Guys.",
  language: "en",
  citations: [{ event_id: "e1", name: "Halal Guys" }],
  results: searchRes.results,
};

beforeEach(() => {
  mockedApi.health.mockResolvedValue({
    status: "ok",
    mode: "mock",
    sessions_active: 1,
    features: { reranking: true, query_expansion: true, spell_correction: true },
  });
  mockedApi.search.mockResolvedValue(searchRes);
  mockedApi.chat.mockResolvedValue(chatRes);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("useRover hook", () => {
  it("loads health on mount", async () => {
    const { result } = renderHook(() => useRover());
    await waitFor(() => expect(result.current.state.health?.mode).toBe("mock"));
  });

  it("sets health null when health fails", async () => {
    mockedApi.health.mockRejectedValue(new Error("down"));
    const { result } = renderHook(() => useRover());
    await waitFor(() => expect(result.current.state.health).toBeNull());
  });

  it("run does nothing on empty query", async () => {
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.run("   ");
    });
    expect(mockedApi.search).not.toHaveBeenCalled();
  });

  it("run with location passes default coordinates", async () => {
    const { result } = renderHook(() => useRover());
    act(() => result.current.setUseLocation(true));
    await act(async () => {
      await result.current.run("halal food open now");
    });
    expect(mockedApi.search).toHaveBeenCalledWith("halal food open now", DEFAULT_LOCATION, 5, expect.any(String));
    expect(result.current.state.response).toEqual(searchRes);
  });

  it("run without location passes null", async () => {
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.run("halal food open now");
    });
    expect(mockedApi.search).toHaveBeenCalledWith("halal food open now", null, 5, expect.any(String));
  });

  it("captures error and clears results", async () => {
    mockedApi.search.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.run("x");
    });
    expect(result.current.state.error).toBe("boom");
    expect(result.current.state.response).toBeNull();
  });

  it("handles non-Error rejection", async () => {
    mockedApi.search.mockRejectedValue("weird");
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.run("x");
    });
    expect(result.current.state.error).toBe("Unknown error");
  });

  it("uses current query when run called with no argument", async () => {
    const { result } = renderHook(() => useRover());
    act(() => result.current.setQuery("stadium"));
    await act(async () => {
      await result.current.run();
    });
    expect(mockedApi.search).toHaveBeenCalledWith("stadium", null, 5, expect.any(String));
  });
});

describe("App", () => {
  it("renders brand and initial empty state", async () => {
    render(<App />);
    expect(screen.getByText(/CrowdCompass/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("mode-chip")).toHaveTextContent("mock"));
  });

  it("runs a search from example chip and shows results", async () => {
    render(<App />);
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("answer-card")).toBeInTheDocument());
    expect(screen.getByTestId("plan-strip")).toBeInTheDocument();
    expect(screen.getByText("Halal Guys")).toBeInTheDocument();
  });

  it("shows feature panel and records history after a search", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("feature-panel")).toBeInTheDocument());
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("history-panel")).toBeInTheDocument());
    expect(screen.getAllByTestId("history-item").length).toBeGreaterThan(0);
  });

  it("replays a query from history", async () => {
    render(<App />);
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("history-panel")).toBeInTheDocument());
    fireEvent.click(screen.getAllByTestId("history-item")[0]);
    await waitFor(() => expect(mockedApi.search).toHaveBeenCalledTimes(2));
  });

  it("shows empty-results state", async () => {
    mockedApi.search.mockResolvedValue({ ...searchRes, results: [] });
    render(<App />);
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("empty")).toBeInTheDocument());
  });

  it("shows error state", async () => {
    mockedApi.search.mockRejectedValue(new Error("network"));
    render(<App />);
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("error")).toHaveTextContent("network"));
  });

  it("typing updates the input value", async () => {
    render(<App />);
    const input = screen.getByLabelText("Ask in any language") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "stadium" } });
    expect(input.value).toBe("stadium");
  });

  it("submits via Ask button after typing and toggles location", async () => {
    render(<App />);
    fireEvent.click(screen.getByRole("checkbox"));
    const input = screen.getByLabelText("Ask in any language") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "stadium" } });
    fireEvent.click(screen.getByText("Ask"));
    await waitFor(() => expect(screen.getByTestId("answer-card")).toBeInTheDocument());
    expect(mockedApi.search).toHaveBeenCalledWith("stadium", DEFAULT_LOCATION, 5, expect.any(String));
  });
});
