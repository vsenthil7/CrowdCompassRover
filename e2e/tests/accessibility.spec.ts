import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// WCAG 2.2 AA accessibility audit of the main search experience.
// Asserts zero serious/critical violations on initial load and after a search.

test("home page has no WCAG 2.2 AA violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical"
  );
  expect(serious).toEqual([]);
});

test("search results region is accessible", async ({ page }) => {
  await page.goto("/");
  const search = page.getByRole("search");
  await expect(search).toBeVisible();
  const input = search.getByRole("textbox").first();
  await input.fill("halal food open now");
  await input.press("Enter");
  // Allow results/answer to render, then re-audit.
  await page.waitForTimeout(1500);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
    .analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical"
  );
  expect(serious).toEqual([]);
});
