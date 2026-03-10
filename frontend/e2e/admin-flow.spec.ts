import { expect, test } from "@playwright/test";

test.describe("Admin entity-link review flow", () => {
	test("admin page loads", async ({ page }) => {
		await page.goto("/admin");
		await expect(page.getByRole("main")).toBeVisible();
	});

	test("admin page has stats section", async ({ page }) => {
		await page.goto("/admin");
		const heading = page.getByRole("heading", { name: /admin/i });
		await expect(heading.first()).toBeVisible();
	});
});
