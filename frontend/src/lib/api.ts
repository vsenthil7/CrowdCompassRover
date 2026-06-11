import type {
  AdminStatus,
  AnalyticsSnapshot,
  AuditReport,
  BulkheadStats,
  ChatAnswer,
  FlagsReport,
  GeoPoint,
  HealthStatus,
  OutboxStats,
  ReadinessReport,
  RelayResult,
  RetentionSweepResult,
  RouteResponse,
  SavedSearch,
  SearchResponse,
  SloReport,
  TracesReport,
  UsageInfo,
  VenueAvailability,
  LiveSignalReport,
  VersionInfo,
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

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new ApiError(res.status, `request failed: ${path}`);
  }
  return (await res.json()) as T;
}

export async function adminStatus(): Promise<AdminStatus> {
  return getJson<AdminStatus>("/admin/status");
}

export async function usage(tenant: string): Promise<UsageInfo> {
  return getJson<UsageInfo>(`/usage/${tenant}`);
}

export async function auditLog(): Promise<AuditReport> {
  return getJson<AuditReport>("/audit");
}

export async function reindex(): Promise<{ indexed: number; healthy: boolean }> {
  return postJson("/admin/reindex", {});
}

export async function flushCache(): Promise<{ flushed: boolean }> {
  return postJson("/admin/cache/flush", {});
}

export async function sloReport(): Promise<SloReport> {
  return getJson<SloReport>("/slo");
}

export async function versionInfo(): Promise<VersionInfo> {
  return getJson<VersionInfo>("/version");
}

export async function outboxStats(): Promise<OutboxStats> {
  return getJson<OutboxStats>("/admin/outbox");
}

export async function outboxRelay(): Promise<RelayResult> {
  return postJson<RelayResult>("/admin/outbox/relay", {});
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

// --- Operator observability endpoints (analytics, traces, flags, readiness, bulkhead) ---

export async function analytics(): Promise<AnalyticsSnapshot> {
  return getJson<AnalyticsSnapshot>("/analytics");
}

export async function traces(): Promise<TracesReport> {
  return getJson<TracesReport>("/traces");
}

export async function flags(): Promise<FlagsReport> {
  return getJson<FlagsReport>("/flags");
}

export async function readiness(): Promise<ReadinessReport> {
  // /ready returns 200 when ready and 503 when not — both carry a JSON body we
  // want to render, so we read the body regardless of status.
  const res = await fetch(`${BASE}/ready`);
  return (await res.json()) as ReadinessReport;
}

export async function bulkheadStats(): Promise<BulkheadStats> {
  return getJson<BulkheadStats>("/admin/bulkhead");
}

export async function sweepRetention(): Promise<RetentionSweepResult> {
  return postJson<RetentionSweepResult>("/admin/retention/sweep", {});
}

// --- Venue availability (opening hours + live crowd) ---

export async function availability(venueId: string, at?: string): Promise<VenueAvailability> {
  const q = at ? `?at=${encodeURIComponent(at)}` : "";
  return getJson<VenueAvailability>(`/availability/${encodeURIComponent(venueId)}${q}`);
}

export async function reportSignal(report: LiveSignalReport): Promise<VenueAvailability> {
  return postJson<VenueAvailability>("/availability/signals", report);
}
