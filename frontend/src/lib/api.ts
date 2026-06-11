import type { ChatAnswer, GeoPoint, SearchResponse } from "./types";

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
): Promise<SearchResponse> {
  return postJson<SearchResponse>("/search", {
    query,
    user_location: userLocation,
    top_k: topK,
  });
}

export async function chat(
  query: string,
  userLocation: GeoPoint | null,
): Promise<ChatAnswer> {
  return postJson<ChatAnswer>("/chat", {
    query,
    user_location: userLocation,
  });
}

export async function health(): Promise<{ status: string; mode: string }> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) {
    throw new ApiError(res.status, "health failed");
  }
  return (await res.json()) as { status: string; mode: string };
}
