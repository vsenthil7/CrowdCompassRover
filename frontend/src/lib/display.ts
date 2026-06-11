import type { VenueCategory } from "./types";

export const CATEGORY_META: Record<VenueCategory, { label: string; glyph: string }> = {
  stadium: { label: "Stadium", glyph: "◈" },
  restaurant: { label: "Food", glyph: "▣" },
  transit: { label: "Transit", glyph: "▷" },
  currency_exchange: { label: "Exchange", glyph: "$" },
  fan_zone: { label: "Fan Zone", glyph: "✦" },
  hospital: { label: "Hospital", glyph: "+" },
  hotel: { label: "Hotel", glyph: "⌂" },
  pop_up_vendor: { label: "Vendor", glyph: "◦" },
  info_kiosk: { label: "Info", glyph: "i" },
};

export const LANGUAGE_LABEL: Record<string, string> = {
  en: "English",
  es: "Español",
  fr: "Français",
  pt: "Português",
  de: "Deutsch",
  ar: "العربية",
};

export function languageLabel(code: string): string {
  return LANGUAGE_LABEL[code] ?? code.toUpperCase();
}

export function formatDistance(km: number | null): string {
  if (km === null) return "";
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(1)} km`;
}

export const TRAVEL_MODE_META: Record<string, { label: string; glyph: string }> = {
  walk: { label: "Walk", glyph: "⊳" },
  transit: { label: "Transit", glyph: "▷" },
  drive: { label: "Drive", glyph: "◈" },
  bicycle: { label: "Cycle", glyph: "⊙" },
};

export function travelModeLabel(mode: string): string {
  return TRAVEL_MODE_META[mode]?.label ?? mode;
}

export function formatCost(cost: number, currency: string): string {
  return cost === 0 ? "Free" : `${cost.toFixed(2)} ${currency}`;
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}
