import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import { getSessionId } from "../lib/session";
import type {
  ChatAnswer,
  GeoPoint,
  HealthStatus,
  HistoryEntry,
  SearchResponse,
} from "../lib/types";

// Default "stadium" location used when the location toggle is on (MetLife Stadium).
export const DEFAULT_LOCATION: GeoPoint = { lat: 40.8135, lon: -74.0745 };

export interface RoverState {
  query: string;
  useLocation: boolean;
  loading: boolean;
  error: string | null;
  response: SearchResponse | null;
  answer: ChatAnswer | null;
  health: HealthStatus | null;
  history: HistoryEntry[];
}

export function useRover() {
  const [query, setQuery] = useState("");
  const [useLocation, setUseLocation] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [answer, setAnswer] = useState<ChatAnswer | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  const refreshHealth = useCallback(() => {
    api
      .health()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

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
        setAnswer(null);
      } finally {
        setLoading(false);
      }
    },
    [query, useLocation, refreshHealth],
  );

  return {
    state: { query, useLocation, loading, error, response, answer, health, history },
    setQuery,
    setUseLocation,
    run,
  };
}
