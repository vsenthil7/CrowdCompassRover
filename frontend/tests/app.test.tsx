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
  next_cursor: null,
  total: 1,
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

  it("routeTo fetches routes and sets routeView", async () => {
    mockedApi.routes.mockResolvedValue({
      options: [
        { mode: "walk", total_distance_km: 1, total_duration_min: 12, estimated_cost: 0, currency: "USD", legs: [] },
      ],
      cheapest: { mode: "walk", total_distance_km: 1, total_duration_min: 12, estimated_cost: 0, currency: "USD", legs: [] },
      fastest: { mode: "walk", total_distance_km: 1, total_duration_min: 12, estimated_cost: 0, currency: "USD", legs: [] },
    });
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.routeTo(searchRes.results[0]);
    });
    expect(result.current.state.routeView?.destinationName).toBe("Halal Guys");
    act(() => result.current.clearRoute());
    expect(result.current.state.routeView).toBeNull();
  });

  it("routeTo captures errors", async () => {
    mockedApi.routes.mockRejectedValue(new Error("route down"));
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.routeTo(searchRes.results[0]);
    });
    expect(result.current.state.error).toBe("route down");
  });

  it("routeTo handles non-Error rejection", async () => {
    mockedApi.routes.mockRejectedValue("weird");
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.routeTo(searchRes.results[0]);
    });
    expect(result.current.state.error).toBe("Unknown error");
  });

  it("loadMore appends results and advances cursor", async () => {
    mockedApi.search.mockResolvedValueOnce({ ...searchRes, next_cursor: "c1", total: 2 });
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.run("food");
    });
    expect(result.current.state.results).toHaveLength(1);
    mockedApi.search.mockResolvedValueOnce({
      ...searchRes,
      results: [{ ...searchRes.results[0], event: { ...searchRes.results[0].event, id: "e2" } }],
      next_cursor: null,
      total: 2,
    });
    await act(async () => {
      await result.current.loadMore();
    });
    expect(result.current.state.results).toHaveLength(2);
    expect(result.current.state.response?.next_cursor).toBeNull();
  });

  it("loadMore is a no-op without a cursor", async () => {
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.run("food");
    });
    const callsBefore = mockedApi.search.mock.calls.length;
    await act(async () => {
      await result.current.loadMore();
    });
    expect(mockedApi.search.mock.calls.length).toBe(callsBefore);
  });

  it("loadMore captures errors", async () => {
    mockedApi.search.mockResolvedValueOnce({ ...searchRes, next_cursor: "c1", total: 2 });
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.run("food");
    });
    mockedApi.search.mockRejectedValueOnce(new Error("page fail"));
    await act(async () => {
      await result.current.loadMore();
    });
    expect(result.current.state.error).toBe("page fail");
  });

  it("loadMore handles non-Error rejection and uses location", async () => {
    mockedApi.search.mockResolvedValueOnce({ ...searchRes, next_cursor: "c1", total: 2 });
    const { result } = renderHook(() => useRover());
    act(() => result.current.setUseLocation(true));
    await act(async () => {
      await result.current.run("food");
    });
    mockedApi.search.mockRejectedValueOnce("weird");
    await act(async () => {
      await result.current.loadMore();
    });
    expect(result.current.state.error).toBe("Unknown error");
    // location was forwarded on the paginated call
    const calls = mockedApi.search.mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall?.[1]).toEqual(DEFAULT_LOCATION);
  });

  it("saveCurrent adds a saved search", async () => {
    mockedApi.saveSearch.mockResolvedValue({ id: "s1", owner: "o", query: "food", label: "food", tags: [] });
    const { result } = renderHook(() => useRover());
    act(() => result.current.setQuery("food"));
    await act(async () => {
      await result.current.saveCurrent();
    });
    expect(result.current.state.saved).toHaveLength(1);
  });

  it("saveCurrent is a no-op with empty query", async () => {
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.saveCurrent();
    });
    expect(mockedApi.saveSearch).not.toHaveBeenCalled();
  });

  it("saveCurrent captures errors", async () => {
    mockedApi.saveSearch.mockRejectedValue(new Error("save fail"));
    const { result } = renderHook(() => useRover());
    act(() => result.current.setQuery("food"));
    await act(async () => {
      await result.current.saveCurrent();
    });
    expect(result.current.state.error).toBe("save fail");
  });

  it("saveCurrent handles non-Error rejection", async () => {
    mockedApi.saveSearch.mockRejectedValue("weird");
    const { result } = renderHook(() => useRover());
    act(() => result.current.setQuery("food"));
    await act(async () => {
      await result.current.saveCurrent();
    });
    expect(result.current.state.error).toBe("Unknown error");
  });

  it("removeSaved deletes a saved search", async () => {
    mockedApi.saveSearch.mockResolvedValue({ id: "s1", owner: "o", query: "food", label: "food", tags: [] });
    mockedApi.deleteSavedSearch.mockResolvedValue(undefined);
    const { result } = renderHook(() => useRover());
    act(() => result.current.setQuery("food"));
    await act(async () => {
      await result.current.saveCurrent();
    });
    await act(async () => {
      await result.current.removeSaved("s1");
    });
    expect(result.current.state.saved).toHaveLength(0);
  });

  it("removeSaved captures errors", async () => {
    mockedApi.deleteSavedSearch.mockRejectedValue(new Error("del fail"));
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.removeSaved("missing");
    });
    expect(result.current.state.error).toBe("del fail");
  });

  it("removeSaved handles non-Error rejection", async () => {
    mockedApi.deleteSavedSearch.mockRejectedValue("weird");
    const { result } = renderHook(() => useRover());
    await act(async () => {
      await result.current.removeSaved("missing");
    });
    expect(result.current.state.error).toBe("Unknown error");
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

  it("opens and closes the route panel from a result row", async () => {
    mockedApi.routes.mockResolvedValue({
      options: [
        { mode: "walk", total_distance_km: 1, total_duration_min: 12, estimated_cost: 0, currency: "USD", legs: [] },
      ],
      cheapest: { mode: "walk", total_distance_km: 1, total_duration_min: 12, estimated_cost: 0, currency: "USD", legs: [] },
      fastest: { mode: "walk", total_distance_km: 1, total_duration_min: 12, estimated_cost: 0, currency: "USD", legs: [] },
    });
    render(<App />);
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("route-button")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("route-button"));
    await waitFor(() => expect(screen.getByTestId("route-panel")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("route-close"));
    await waitFor(() => expect(screen.queryByTestId("route-panel")).toBeNull());
  });

  it("paginates with Show more", async () => {
    mockedApi.search.mockResolvedValueOnce({ ...searchRes, next_cursor: "c1", total: 2 });
    render(<App />);
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("pagination")).toBeInTheDocument());
    mockedApi.search.mockResolvedValueOnce({
      ...searchRes,
      results: [{ ...searchRes.results[0], event: { ...searchRes.results[0].event, id: "e2" } }],
      next_cursor: null,
      total: 2,
    });
    fireEvent.click(screen.getByTestId("pagination-next"));
    await waitFor(() => expect(screen.getByTestId("pagination-end")).toBeInTheDocument());
  });

  it("saves and lists a saved search", async () => {
    mockedApi.saveSearch.mockResolvedValue({ id: "s1", owner: "o", query: "halal food open now", label: "halal food open now", tags: [] });
    mockedApi.deleteSavedSearch.mockResolvedValue(undefined);
    render(<App />);
    fireEvent.click(screen.getByText("halal food open now"));
    await waitFor(() => expect(screen.getByTestId("saved-add")).toBeInTheDocument());
    fireEvent.click(screen.getByTestId("saved-add"));
    await waitFor(() => expect(screen.getByTestId("saved-run")).toBeInTheDocument());
    // run the saved search from the list
    fireEvent.click(screen.getByTestId("saved-run"));
    await waitFor(() => expect(mockedApi.search).toHaveBeenCalledTimes(2));
    // delete it
    fireEvent.click(screen.getByTestId("saved-delete"));
    await waitFor(() => expect(screen.queryByTestId("saved-run")).toBeNull());
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
