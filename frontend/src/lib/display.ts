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
