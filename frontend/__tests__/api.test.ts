import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock fetch globally before importing the module
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

describe("apiFetch (via searchPersons)", () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("constructs correct URL with query params", async () => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: () => Promise.resolve({ results: [], total: 0 }),
		});

		const { searchPersons } = await import("@/lib/api");
		await searchPersons("graph neural", 5);

		expect(mockFetch).toHaveBeenCalledOnce();
		const [url] = mockFetch.mock.calls[0];
		expect(url).toContain("/search?");
		expect(url).toContain("q=graph+neural");
		expect(url).toContain("limit=5");
	});

	it("throws on non-ok response", async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 403,
			statusText: "Forbidden",
			text: () => Promise.resolve("Forbidden"),
		});

		const { searchPersons } = await import("@/lib/api");
		await expect(searchPersons("test")).rejects.toThrow("API 403");
	});

	it("returns undefined for 204 No Content", async () => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 204,
			json: () => Promise.reject(new Error("no body")),
		});

		const { deleteShortlist } = await import("@/lib/api");
		const result = await deleteShortlist("some-id");
		expect(result).toBeUndefined();
	});

	it("sends X-API-Key header", async () => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: () => Promise.resolve({ results: [], total: 0 }),
		});

		const { searchPersons } = await import("@/lib/api");
		await searchPersons("test");

		const [, init] = mockFetch.mock.calls[0];
		expect(init.headers["X-API-Key"]).toBeDefined();
	});
});
