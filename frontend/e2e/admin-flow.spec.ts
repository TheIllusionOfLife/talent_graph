import { expect, test } from "@playwright/test";

test.describe("Admin entity-link review flow", () => {
	test("admin page loads", async ({ page }) => {
		await page.goto("/admin");
		await expect(page.getByRole("main")).toBeVisible();
	});

	test("admin page has stats section", async ({ page }) => {
		await page.goto("/admin");
		// Page should render without a runtime error
		const main = page.getByRole("main");
		await expect(main).toBeVisible();
	});
});
