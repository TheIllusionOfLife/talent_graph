import { expect, test } from "@playwright/test";

test.describe("Shortlist flow", () => {
	test("shortlists page loads", async ({ page }) => {
		await page.goto("/shortlists");
		await expect(page.getByRole("main")).toBeVisible();
	});

	test("shortlists page has expected heading", async ({ page }) => {
		await page.goto("/shortlists");
		// Should show some heading text related to shortlists
		const heading = page.getByRole("heading");
		await expect(heading.first()).toBeVisible();
	});
});
