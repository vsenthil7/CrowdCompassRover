import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import { getSessionId } from "../lib/session";
import type {
  ChatAnswer,
  GeoPoint,
  HealthStatus,
  HistoryEntry,
  RouteResponse,
  SavedSearch,
  ScoredEvent,
  SearchResponse,
} from "../lib/types";

// Default "stadium" location used when the location toggle is on (MetLife Stadium).
export const DEFAULT_LOCATION: GeoPoint = { lat: 40.8135, lon: -74.0745 };

export interface RouteView {
  destinationName: string;
  routes: RouteResponse;
}

export interface RoverState {
  query: string;
  useLocation: boolean;
  loading: boolean;
  error: string | null;
  response: SearchResponse | null;
  results: ScoredEvent[];
  answer: ChatAnswer | null;
  health: HealthStatus | null;
  history: HistoryEntry[];
  routeView: RouteView | null;
  routeLoading: boolean;
  saved: SavedSearch[];
  saving: boolean;
  pageLoading: boolean;
}

export function useRover() {
  const [query, setQuery] = useState("");
  const [useLocation, setUseLocation] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [results, setResults] = useState<ScoredEvent[]>([]);
  const [answer, setAnswer] = useState<ChatAnswer | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [routeView, setRouteView] = useState<RouteView | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);
  const [saved, setSaved] = useState<SavedSearch[]>([]);
  const [saving, setSaving] = useState(false);
  const [pageLoading, setPageLoading] = useState(false);

  const refreshHealth = useCallback(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  const locationOrNull = useLocation ? DEFAULT_LOCATION : null;

  const run = useCallback(
    async (q?: string) => {
      const text = (q ?? query).trim();
      if (!text) return;
      setQuery(text);
      setLoading(true);
      setError(null);
      const loc = useLocation ? DEFAULT_LOCATION : null;
      const sessionId = getSessionId();
      try {
        const [searchRes, chatRes] = await Promise.all([
          api.search(text, loc, 5, sessionId),
          api.chat(text, loc, sessionId),
        ]);
        setResponse(searchRes);
        setResults(searchRes.results);
        setAnswer(chatRes);
        setHistory((prev) => [
          {
            id: `${Date.now()}-${prev.length}`,
            query: text,
            language: searchRes.plan.detected_language,
            resultCount: searchRes.results.length,
          },
          ...prev,
        ]);
        refreshHealth();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
        setResponse(null);
        setResults([]);
        setAnswer(null);
      } finally {
        setLoading(false);
      }
    },
    [query, useLocation, refreshHealth],
  );

  const loadMore = useCallback(async () => {
    if (!response?.next_cursor) return;
    setPageLoading(true);
    try {
      const next = await api.search(
        query,
        useLocation ? DEFAULT_LOCATION : null,
        5,
        getSessionId(),
        response.next_cursor,
      );
      setResults((prev) => [...prev, ...next.results]);
      setResponse(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setPageLoading(false);
    }
  }, [response, query, useLocation]);

  const routeTo = useCallback(async (hit: ScoredEvent) => {
    setRouteLoading(true);
    try {
      const res = await api.routes(DEFAULT_LOCATION, hit.event.location, null);
      setRouteView({ destinationName: hit.event.name, routes: res });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setRouteLoading(false);
    }
  }, []);

  const clearRoute = useCallback(() => setRouteView(null), []);

  const saveCurrent = useCallback(async () => {
    if (!query.trim()) return;
    setSaving(true);
    try {
      const s = await api.saveSearch(getSessionId(), query, query);
      setSaved((prev) => [s, ...prev]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  }, [query]);

  const removeSaved = useCallback(async (id: string) => {
    try {
      await api.deleteSavedSearch(getSessionId(), id);
      setSaved((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
  }, []);

  return {
    state: {
      query,
      useLocation,
      loading,
      error,
      response,
      results,
      answer,
      health,
      history,
      routeView,
      routeLoading,
      saved,
      saving,
      pageLoading,
      locationOrNull,
    },
    setQuery,
    setUseLocation,
    run,
    loadMore,
    routeTo,
    clearRoute,
    saveCurrent,
    removeSaved,
  };
}
