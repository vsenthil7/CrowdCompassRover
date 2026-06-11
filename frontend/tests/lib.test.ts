import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { CATEGORY_META, formatDistance, languageLabel } from "../src/lib/display";
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
    fetchMock.mockResolvedValue({ ok: true, json: async () => ({ status: "ok", mode: "mock" }) });
    const h = await api.health();
    expect(h.mode).toBe("mock");
  });

  it("health throws on failure", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 503 });
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
  });
});
