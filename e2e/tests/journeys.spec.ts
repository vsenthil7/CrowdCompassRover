import { test, expect } from "@playwright/test";

// Full user journeys against the real backend (mock mode) + built frontend.

test.describe("CrowdCompass Rover — core journeys", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("mode-chip")).toContainText("mock");
  });

  test("J1: landing shows brand and prompt", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /CrowdCompass/ })).toBeVisible();
    await expect(page.getByText(/Ask for stadiums, food, transit/)).toBeVisible();
  });

  test("J2: English halal+open search returns grounded answer and results", async ({ page }) => {
    await page.getByText("halal food open now", { exact: true }).click();
    await expect(page.getByTestId("answer-card")).toBeVisible();
    await expect(page.getByTestId("plan-strip")).toContainText("English");
    await expect(page.getByTestId("plan-strip")).toContainText("Halal");
    const rows = page.getByTestId("result-row");
    await expect(rows.first()).toBeVisible();
  });

  test("J3: Spanish query is detected and answered in Spanish", async ({ page }) => {
    await page.getByLabelText("Ask in any language").fill("dónde cambiar dinero ahora");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByTestId("plan-strip")).toContainText("Español");
    await expect(page.getByTestId("answer-card")).toContainText(/Esto es lo que encontré|encontré/);
  });

  test("J4: French stadium query detected", async ({ page }) => {
    await page.getByLabelText("Ask in any language").fill("où est le stade");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByTestId("plan-strip")).toContainText("Français");
    await expect(page.getByTestId("result-row").first()).toContainText(/Stadium|Estadio|Azteca|MetLife|SoFi/);
  });

  test("J5: location toggle yields distances", async ({ page }) => {
    await page.getByRole("checkbox").check();
    await page.getByLabelText("Ask in any language").fill("nearest transit to stadium");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByTestId("plan-strip")).toContainText("Transit");
    await expect(page.getByText(/km|m$/).first()).toBeVisible();
  });

  test("J6: Enter key submits", async ({ page }) => {
    const input = page.getByLabelText("Ask in any language");
    await input.fill("fan zone");
    await input.press("Enter");
    await expect(page.getByTestId("answer-card")).toBeVisible();
  });

  test("J7: Ask button disabled when empty", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  test("J8: nonsense query shows empty state", async ({ page }) => {
    await page.getByLabelText("Ask in any language").fill("zzzz qqqq in atlantis city");
    await page.getByRole("button", { name: "Ask" }).click();
    // Either empty board or no rows; plan strip still renders.
    await expect(page.getByTestId("plan-strip")).toBeVisible();
  });
});
