import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { CATEGORY_META, formatCost, formatDistance, formatDuration, languageLabel, travelModeLabel } from "../src/lib/display";
import * as api from "../src/lib/api";
import { ApiError } from "../src/lib/api";

describe("display helpers", () => {
  it("has metadata for every category", () => {
    expect(CATEGORY_META.stadium.label).toBe("Stadium");
    expect(CATEGORY_META.currency_exchange.glyph).toBeTruthy();
  });

  it("formats distance below 1km as metres", () => {
    expect(formatDistance(0.42)).toBe("420 m");
  });

  it("formats distance above 1km as km", () => {
    expect(formatDistance(3.456)).toBe("3.5 km");
  });

  it("returns empty for null distance", () => {
    expect(formatDistance(null)).toBe("");
  });

  it("maps known language codes and falls back", () => {
    expect(languageLabel("es")).toBe("Español");
    expect(languageLabel("zz")).toBe("ZZ");
  });

  it("formats travel mode labels with fallback", () => {
    expect(travelModeLabel("walk")).toBe("Walk");
    expect(travelModeLabel("teleport")).toBe("teleport");
  });

  it("formats cost as Free or amount", () => {
    expect(formatCost(0, "USD")).toBe("Free");
    expect(formatCost(2.5, "USD")).toBe("2.50 USD");
  });

  it("formats duration in minutes and hours", () => {
    expect(formatDuration(45)).toBe("45 min");
    expect(formatDuration(120)).toBe("2 h");
    expect(formatDuration(90)).toBe("1 h 30 min");
  });
});

describe("api client", () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("search posts and returns json", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ plan: {}, results: [] }) });
    const res = await api.search("q", { lat: 1, lon: 2 }, 5);
    expect(res.results).toEqual([]);
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body).query).toBe("q");
  });

  it("chat posts and returns json", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ answer: "hi", language: "en", citations: [], results: [] }) });
    const res = await api.chat("q", null);
    expect(res.answer).toBe("hi");
  });

  it("throws ApiError on non-ok search", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 });
    await expect(api.search("q", null, 5)).rejects.toBeInstanceOf(ApiError);
  });

  it("health returns mode", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        mode: "mock",
        sessions_active: 0,
        features: { reranking: true, query_expansion: true, spell_correction: true },
      }),
    });
    const h = await api.health();
    expect(h.mode).toBe("mock");
  });

  it("health throws on failure", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 503 });
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
  });

  it("routes posts origin/destination and returns options", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ options: [], cheapest: null, fastest: null }),
    });
    const res = await api.routes({ lat: 1, lon: 2 }, { lat: 3, lon: 4 }, ["walk"]);
    expect(res.options).toEqual([]);
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body).modes).toEqual(["walk"]);
  });

  it("search passes cursor when provided", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ plan: {}, results: [], next_cursor: null, total: 0 }),
    });
    await api.search("q", null, 5, "sess", "cur123");
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body).cursor).toBe("cur123");
  });

  it("saveSearch posts owner/query/label", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ id: "s1", owner: "o", query: "q", label: "l", tags: [] }),
    });
    const res = await api.saveSearch("o", "q", "l");
    expect(res.id).toBe("s1");
    const [, init] = fetchMock.mock.calls[0];
    expect(JSON.parse(init.body).owner).toBe("o");
  });

  it("deleteSavedSearch calls DELETE", async () => {
    fetchMock.mockResolvedValue({ ok: true });
    await api.deleteSavedSearch("o", "s1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/saved-searches/o/s1");
    expect(init.method).toBe("DELETE");
  });

  it("deleteSavedSearch throws on failure", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404 });
    await expect(api.deleteSavedSearch("o", "s1")).rejects.toBeInstanceOf(ApiError);
  });

  it("adminStatus fetches status", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ events: 16, cache_size: 0, cache_hit_rate: 0.5, data_stale: false, data_age_seconds: 5, flags: {} }),
    });
    const s = await api.adminStatus();
    expect(s.events).toBe(16);
  });

  it("usage fetches tenant usage", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ tenant: "t", period: "2026-06", count: 3, by_action: {}, remaining: 7, quota: 10 }),
    });
    const u = await api.usage("t");
    expect(u.remaining).toBe(7);
  });

  it("auditLog fetches audit report", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ verified: true, count: 0, entries: [] }),
    });
    const a = await api.auditLog();
    expect(a.verified).toBe(true);
  });

  it("getJson throws on failure", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500 });
    await expect(api.adminStatus()).rejects.toBeInstanceOf(ApiError);
  });

  it("reindex and flushCache post", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ indexed: 16, healthy: true }) });
    const r = await api.reindex();
    expect(r.indexed).toBe(16);
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ flushed: true }) });
    const f = await api.flushCache();
    expect(f.flushed).toBe(true);
  });

  it("sloReport fetches services", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ services: [] }) });
    const s = await api.sloReport();
    expect(s.services).toEqual([]);
  });

  it("versionInfo fetches version", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ current: "v1", supported: ["v1"] }) });
    const v = await api.versionInfo();
    expect(v.current).toBe("v1");
  });

  it("outboxStats fetches stats", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ stats: { pending: 1, delivered: 2, failed: 0, dead: 0 }, dead_letters: [] }),
    });
    const o = await api.outboxStats();
    expect(o.stats.delivered).toBe(2);
  });

  it("outboxRelay posts", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ delivered: 1, failed: 0, dead: 0 }) });
    const r = await api.outboxRelay();
    expect(r.delivered).toBe(1);
  });

  it("analytics fetches a snapshot", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ total: 5, zero_result: 1, zero_result_rate: 0.2, by_language: {}, by_category: {}, top_queries: [] }),
    });
    const a = await api.analytics();
    expect(a.total).toBe(5);
  });

  it("traces fetches spans", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ spans: [] }) });
    const t = await api.traces();
    expect(t.spans).toEqual([]);
  });

  it("flags fetches evaluated flags", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ flags: { x: true } }) });
    const f = await api.flags();
    expect(f.flags.x).toBe(true);
  });

  it("readiness reads the body regardless of status code", async () => {
    // 503 (not ready) still carries a JSON body we render.
    fetchMock.mockResolvedValue({ ok: false, status: 503, json: async () => ({ state: "degraded", ready: false, components: [] }) });
    const r = await api.readiness();
    expect(r.ready).toBe(false);
  });

  it("bulkheadStats fetches utilisation", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ name: "search", max_concurrent: 16, active: 1, queued: 0, rejected: 0 }),
    });
    const b = await api.bulkheadStats();
    expect(b.name).toBe("search");
  });

  it("sweepRetention posts", async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ swept: [{ name: "analytics", removed: 2 }] }) });
    const s = await api.sweepRetention();
    expect(s.swept[0].removed).toBe(2);
  });

  it("availability fetches venue status", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        venue_id: "v1", open_state: "open", is_open: true, effectively_open: true,
        minutes_to_transition: null, crowd: "quiet", wait_minutes: null,
        temporarily_closed: false, note: "",
      }),
    });
    const a = await api.availability("v1");
    expect(a.open_state).toBe("open");
    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/availability/v1");
  });

  it("availability passes the 'at' query param", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        venue_id: "v1", open_state: "closed", is_open: false, effectively_open: false,
        minutes_to_transition: null, crowd: "unknown", wait_minutes: null,
        temporarily_closed: false, note: "",
      }),
    });
    await api.availability("v1", "2026-06-02T04:00:00Z");
    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("at=");
  });

  it("reportSignal posts a live signal", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        venue_id: "v1", open_state: "open", is_open: true, effectively_open: true,
        minutes_to_transition: null, crowd: "packed", wait_minutes: 30,
        temporarily_closed: false, note: "",
      }),
    });
    const a = await api.reportSignal({ venue_id: "v1", crowd: "packed", wait_minutes: 30 });
    expect(a.crowd).toBe("packed");
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
  });
});
