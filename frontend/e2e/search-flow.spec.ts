import { expect, test } from "@playwright/test";

test.describe("Search → Discovery → Person Detail flow", () => {
	test("search bar is visible on home page", async ({ page }) => {
		await page.goto("/");
		const searchInput = page.getByRole("textbox");
		await expect(searchInput).toBeVisible();
	});

	test("home page loads successfully", async ({ page }) => {
		await page.goto("/");
		await expect(page).toHaveTitle(/talent/i);
	});

	test("navigating to discovery page works", async ({ page }) => {
		await page.goto("/discovery/concept/test-id");
		const heading = page.getByRole("heading", { name: /discovery/i });
		await expect(heading).toBeVisible();
	});
});
