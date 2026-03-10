import { expect, type Page, test } from "@playwright/test";

async function mockSearchesApi(page: Page): Promise<void> {
	await page.route("**/searches", (route) => {
		if (route.request().resourceType() === "document") {
			return route.continue();
		}
		return route.fulfill({ json: [] });
	});
}

test.describe("Saved Searches page", () => {
	test("loads with 'Saved Searches' heading", async ({ page }) => {
		await mockSearchesApi(page);
		await page.goto("/searches");
		const heading = page.getByRole("heading", { name: /saved searches/i });
		await expect(heading).toBeVisible();
	});

	test("shows empty state message when API returns no results", async ({
		page,
	}) => {
		await mockSearchesApi(page);
		await page.goto("/searches");
		await expect(page.getByText(/no saved searches yet/i)).toBeVisible();
	});

	test("back link (← Search) is present and points to /", async ({ page }) => {
		await mockSearchesApi(page);
		await page.goto("/searches");
		const backLink = page.getByRole("link", { name: "← Search" });
		await expect(backLink).toBeVisible();
		await expect(backLink).toHaveAttribute("href", "/");
	});

	test("nav link to Saved Searches is visible from home page", async ({
		page,
	}) => {
		await page.goto("/");
		const navLink = page.getByRole("link", { name: "Saved Searches" });
		await expect(navLink).toBeVisible();
	});
});
