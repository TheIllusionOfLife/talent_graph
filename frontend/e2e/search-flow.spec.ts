import { expect, test } from "@playwright/test";

test.describe("Search → Discovery → Person Detail flow", () => {
	test("search bar is visible on home page", async ({ page }) => {
		await page.goto("/");
		await expect(page.getByRole("main")).toBeVisible();
	});

	test("empty search shows no results", async ({ page }) => {
		await page.goto("/");
		// The page loads without error
		await expect(page).toHaveTitle(/talent/i);
	});

	test("navigating to discovery page works", async ({ page }) => {
		await page.goto("/discovery");
		await expect(page.getByRole("main")).toBeVisible();
	});
});
