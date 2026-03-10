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

test.describe("Save search flow", () => {
	test("Save button appears after typing in search bar", async ({ page }) => {
		await page.goto("/");
		const searchInput = page.getByPlaceholder(/search for researchers/i);
		await searchInput.fill("machine learning");
		const saveButton = page.getByRole("button", { name: /^save$/i });
		await expect(saveButton).toBeVisible();
	});

	test("clicking Save reveals the name input field", async ({ page }) => {
		await page.goto("/");
		const searchInput = page.getByPlaceholder(/search for researchers/i);
		await searchInput.fill("machine learning");
		await page.getByRole("button", { name: /^save$/i }).click();
		const nameInput = page.getByPlaceholder(/name this search/i);
		await expect(nameInput).toBeVisible();
	});

	test("Cancel button closes the save form", async ({ page }) => {
		await page.goto("/");
		const searchInput = page.getByPlaceholder(/search for researchers/i);
		await searchInput.fill("machine learning");
		await page.getByRole("button", { name: /^save$/i }).click();
		await expect(page.getByPlaceholder(/name this search/i)).toBeVisible();
		await page.getByRole("button", { name: /cancel/i }).click();
		await expect(page.getByPlaceholder(/name this search/i)).not.toBeVisible();
	});
});
