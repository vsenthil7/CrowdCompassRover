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
