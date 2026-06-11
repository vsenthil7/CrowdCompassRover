export type VenueCategory =
  | "stadium"
  | "restaurant"
  | "transit"
  | "currency_exchange"
  | "fan_zone"
  | "hospital"
  | "hotel"
  | "pop_up_vendor"
  | "info_kiosk";

export interface GeoPoint {
  lat: number;
  lon: number;
}

export interface CityEvent {
  id: string;
  name: string;
  category: VenueCategory;
  city: string;
  description: string;
  languages: string[];
  location: GeoPoint;
  open_now: boolean;
  tags: string[];
  halal: boolean;
  vegetarian: boolean;
  wheelchair_accessible: boolean;
  capacity: number | null;
}

export interface ScoredEvent {
  event: CityEvent;
  score: number;
  distance_km: number | null;
}

export interface SearchFilters {
  city?: string | null;
  category?: VenueCategory | null;
  open_now?: boolean | null;
  halal?: boolean | null;
  vegetarian?: boolean | null;
  wheelchair_accessible?: boolean | null;
}

export interface QueryPlan {
  original_query: string;
  detected_language: string;
  normalized_query: string;
  semantic_text: string;
  filters: SearchFilters;
  top_k: number;
}

export interface SearchResponse {
  plan: QueryPlan;
  results: ScoredEvent[];
  next_cursor: string | null;
  total: number | null;
}

export interface SavedSearch {
  id: string;
  owner: string;
  query: string;
  label: string;
  tags: string[];
}

export interface AdminStatus {
  events: number;
  cache_size: number;
  cache_hit_rate: number;
  data_stale: boolean;
  data_age_seconds: number;
  flags: Record<string, boolean>;
}

export interface UsageInfo {
  tenant: string;
  period: string;
  count: number;
  by_action: Record<string, number>;
  remaining: number;
  quota: number;
}

export interface AuditEntry {
  seq: number;
  actor: string;
  tenant: string;
  action: string;
  resource: string;
  outcome: string;
  ts: number;
}

export interface AuditReport {
  verified: boolean;
  count: number;
  entries: AuditEntry[];
}

export interface SloService {
  service: string;
  target: number;
  total: number;
  success_ratio: number;
  meeting_slo: boolean;
  budget_remaining: number;
}

export interface SloReport {
  services: SloService[];
}

export interface VersionInfo {
  current: string;
  supported: string[];
}

export interface OutboxStats {
  stats: { pending: number; delivered: number; failed: number; dead: number };
  dead_letters: { id: string; topic: string; attempts: number; error: string | null }[];
}

export interface RelayResult {
  delivered: number;
  failed: number;
  dead: number;
}

export interface Citation {
  event_id: string;
  name: string;
}

export interface ChatAnswer {
  answer: string;
  language: string;
  citations: Citation[];
  results: ScoredEvent[];
}

export interface HealthFeatures {
  reranking: boolean;
  query_expansion: boolean;
  spell_correction: boolean;
}

export interface HealthStatus {
  status: string;
  mode: string;
  sessions_active: number;
  features: HealthFeatures;
}

export interface HistoryEntry {
  id: string;
  query: string;
  language: string;
  resultCount: number;
}

export type TravelMode = "walk" | "transit" | "drive" | "bicycle";

export interface RouteLeg {
  mode: TravelMode;
  instruction: string;
  distance_km: number;
  duration_min: number;
}

export interface RouteOption {
  mode: TravelMode;
  total_distance_km: number;
  total_duration_min: number;
  estimated_cost: number;
  currency: string;
  legs: RouteLeg[];
}

export interface RouteResponse {
  options: RouteOption[];
  cheapest: RouteOption | null;
  fastest: RouteOption | null;
}

// --- Operator observability surfaces (analytics, traces, flags, health, bulkhead) ---

export interface AnalyticsSnapshot {
  total: number;
  zero_result: number;
  zero_result_rate: number;
  by_language: Record<string, number>;
  by_category: Record<string, number>;
  top_queries: [string, number][];
}

export interface TraceSpan {
  trace_id: string;
  span_id: string;
  parent_id: string | null;
  name: string;
  duration_ms: number;
  status: string;
  attributes: Record<string, unknown>;
}

export interface TracesReport {
  spans: TraceSpan[];
}

export interface FlagsReport {
  flags: Record<string, boolean>;
}

export interface ComponentHealth {
  name: string;
  state: string;
  detail: string;
  latency_ms: number;
}

export interface ReadinessReport {
  state: string;
  ready: boolean;
  components: ComponentHealth[];
}

export interface BulkheadStats {
  name: string;
  max_concurrent: number;
  active: number;
  queued: number;
  max_queue?: number;
  rejected?: number;
}

export interface RetentionSweepResult {
  swept: { name: string; removed: number }[];
}

// --- Venue availability (opening hours + live crowd signals) ---

export type OpenStateValue = "open" | "closed" | "opening_soon" | "closing_soon";
export type CrowdValue = "quiet" | "moderate" | "busy" | "packed" | "unknown";

export interface VenueAvailability {
  venue_id: string;
  open_state: OpenStateValue;
  is_open: boolean;
  effectively_open: boolean;
  minutes_to_transition: number | null;
  crowd: CrowdValue;
  wait_minutes: number | null;
  temporarily_closed: boolean;
  note: string;
}

export interface LiveSignalReport {
  venue_id: string;
  crowd?: CrowdValue;
  wait_minutes?: number;
  temporarily_closed?: boolean;
  note?: string;
}
