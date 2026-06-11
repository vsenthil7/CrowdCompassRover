import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import type { ChatAnswer, GeoPoint, SearchResponse } from "../lib/types";

// Default "stadium" location used when the location toggle is on (MetLife Stadium).
export const DEFAULT_LOCATION: GeoPoint = { lat: 40.8135, lon: -74.0745 };

export interface RoverState {
  query: string;
  useLocation: boolean;
  loading: boolean;
  error: string | null;
  response: SearchResponse | null;
  answer: ChatAnswer | null;
  mode: string;
}

export function useRover() {
  const [query, setQuery] = useState("");
  const [useLocation, setUseLocation] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [answer, setAnswer] = useState<ChatAnswer | null>(null);
  const [mode, setMode] = useState<string>("");

  useEffect(() => {
    api
      .health()
      .then((h) => setMode(h.mode))
      .catch(() => setMode("unknown"));
  }, []);

  const run = useCallback(
    async (q?: string) => {
      const text = (q ?? query).trim();
      if (!text) return;
      setQuery(text);
      setLoading(true);
      setError(null);
      const loc = useLocation ? DEFAULT_LOCATION : null;
      try {
        const [searchRes, chatRes] = await Promise.all([
          api.search(text, loc, 5),
          api.chat(text, loc),
        ]);
        setResponse(searchRes);
        setAnswer(chatRes);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
        setResponse(null);
        setAnswer(null);
      } finally {
        setLoading(false);
      }
    },
    [query, useLocation],
  );

  return {
    state: { query, useLocation, loading, error, response, answer, mode },
    setQuery,
    setUseLocation,
    run,
  };
}
