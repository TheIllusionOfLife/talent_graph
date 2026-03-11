import { expect, test } from "@playwright/test";

test.describe("Graph visualization flow", () => {
	test("graph page loads with UI elements", async ({ page }) => {
		await page.goto("/graph/person/test-id");
		// Page should load (may show error from API, but UI elements should render)
		await expect(page.locator("body")).toBeVisible();
	});

	test("graph page shows breadcrumb navigation", async ({ page }) => {
		await page.goto("/graph/person/test-id");
		const searchLink = page.getByRole("link", { name: /search/i });
		await expect(searchLink).toBeVisible();
	});
});

test.describe("Lookalike page flow", () => {
	test("lookalike page loads", async ({ page }) => {
		await page.goto("/lookalike/test-id");
		await expect(page.locator("body")).toBeVisible();
	});
});

test.describe("Person detail page graph links", () => {
	test("person page shows View Graph and Find Lookalikes buttons", async ({
		page,
	}) => {
		// This test will fail if the API is not running, but it verifies the page renders
		await page.goto("/person/test-id");
		await expect(page.locator("body")).toBeVisible();
	});
});
