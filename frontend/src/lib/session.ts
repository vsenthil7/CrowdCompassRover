// Generates and holds a stable session id for the lifetime of the page load, so the
// backend can carry multi-turn conversation context across queries.

let cached: string | null = null;

export function createSessionId(): string {
  const rand = Math.random().toString(36).slice(2, 10);
  const time = Date.now().toString(36);
  return `web-${time}-${rand}`;
}

export function getSessionId(): string {
  if (cached === null) {
    cached = createSessionId();
  }
  return cached;
}

// Test-only hook to reset the cached id between cases.
export function _resetSessionId(): void {
  cached = null;
}
