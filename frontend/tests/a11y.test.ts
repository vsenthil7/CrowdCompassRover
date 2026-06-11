import { describe, expect, it, vi } from "vitest";
import {
  ariaLiveFor,
  formatAge,
  formatPercent,
  isActivateKey,
  onActivate,
} from "../src/lib/a11y";

describe("a11y helpers", () => {
  it("recognises activation keys", () => {
    expect(isActivateKey("Enter")).toBe(true);
    expect(isActivateKey(" ")).toBe(true);
    expect(isActivateKey("Spacebar")).toBe(true);
    expect(isActivateKey("a")).toBe(false);
  });

  it("onActivate fires handler and prevents default on activation key", () => {
    const handler = vi.fn();
    const preventDefault = vi.fn();
    onActivate(handler)({ key: "Enter", preventDefault } as never);
    expect(handler).toHaveBeenCalled();
    expect(preventDefault).toHaveBeenCalled();
  });

  it("onActivate ignores non-activation keys", () => {
    const handler = vi.fn();
    const preventDefault = vi.fn();
    onActivate(handler)({ key: "Tab", preventDefault } as never);
    expect(handler).not.toHaveBeenCalled();
    expect(preventDefault).not.toHaveBeenCalled();
  });

  it("maps severity to aria-live politeness", () => {
    expect(ariaLiveFor("critical")).toBe("assertive");
    expect(ariaLiveFor("warning")).toBe("polite");
    expect(ariaLiveFor("info")).toBe("polite");
  });

  it("formats age in s/m/h", () => {
    expect(formatAge(30)).toBe("30s");
    expect(formatAge(120)).toBe("2m");
    expect(formatAge(7200)).toBe("2h");
  });

  it("formats percent to one decimal", () => {
    expect(formatPercent(0.5)).toBe("50%");
    expect(formatPercent(0.1234)).toBe("12.3%");
  });
});
