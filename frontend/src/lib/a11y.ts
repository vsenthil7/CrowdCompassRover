// Accessibility helpers: keyboard-activation and focus utilities shared across components.
// Keeps a11y logic in one tested place rather than scattering inline handlers.

import type { KeyboardEvent } from "react";

// Returns true when a keyboard event should "activate" a control (Enter or Space).
export function isActivateKey(key: string): boolean {
  return key === "Enter" || key === " " || key === "Spacebar";
}

// Wraps a callback so it fires on Enter/Space and prevents the default scroll-on-space.
export function onActivate(handler: () => void) {
  return (event: KeyboardEvent) => {
    if (isActivateKey(event.key)) {
      event.preventDefault();
      handler();
    }
  };
}

// Builds an aria-live politeness value from a severity-like string.
export function ariaLiveFor(severity: "info" | "warning" | "critical"): "polite" | "assertive" {
  return severity === "critical" ? "assertive" : "polite";
}

// Formats a number of seconds into a short human label for screen readers and chips.
export function formatAge(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
}

// Percentage formatter used by usage and cache-hit displays.
export function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 1000) / 10}%`;
}
