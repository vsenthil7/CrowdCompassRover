import type {
  ChatAnswer,
  GeoPoint,
  HealthStatus,
  RouteResponse,
  SavedSearch,
  SearchResponse,
} from "./types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function search(
  query: string,
  userLocation: GeoPoint | null,
  topK: number,
  sessionId: string | null = null,
  cursor: string | null = null,
): Promise<SearchResponse> {
  return postJson<SearchResponse>("/search", {
    query,
    user_location: userLocation,
    top_k: topK,
    session_id: sessionId,
    cursor,
  });
}

export async function saveSearch(
  owner: string,
  query: string,
  label: string,
): Promise<SavedSearch> {
  return postJson<SavedSearch>("/saved-searches", { owner, query, label, tags: [] });
}

export async function deleteSavedSearch(owner: string, id: string): Promise<void> {
  const res = await fetch(`${BASE}/saved-searches/${owner}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    throw new ApiError(res.status, "delete failed");
  }
}

export async function chat(
  query: string,
  userLocation: GeoPoint | null,
  sessionId: string | null = null,
): Promise<ChatAnswer> {
  return postJson<ChatAnswer>("/chat", {
    query,
    user_location: userLocation,
    session_id: sessionId,
  });
}

export async function health(): Promise<HealthStatus> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) {
    throw new ApiError(res.status, "health failed");
  }
  return (await res.json()) as HealthStatus;
}

export async function routes(
  origin: GeoPoint,
  destination: GeoPoint,
  modes: string[] | null = null,
): Promise<RouteResponse> {
  return postJson<RouteResponse>("/routes", {
    origin,
    destination,
    modes,
  });
}
