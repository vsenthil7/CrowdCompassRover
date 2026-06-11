import { describe, expect, it } from "vitest";
import * as api from "../src/lib/api";

describe("authHeaders", () => {
  it("returns the base headers unchanged when no key is present", () => {
    expect(api.authHeaders({ "Content-Type": "application/json" }, "")).toEqual({
      "Content-Type": "application/json",
    });
  });

  it("adds X-API-Key when a key is supplied", () => {
    expect(api.authHeaders({ "Content-Type": "application/json" }, "k-123")).toEqual({
      "Content-Type": "application/json",
      "X-API-Key": "k-123",
    });
  });

  it("defaults to an empty base object", () => {
    expect(api.authHeaders(undefined, "k-9")).toEqual({ "X-API-Key": "k-9" });
  });
});
