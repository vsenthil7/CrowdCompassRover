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
