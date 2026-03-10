// API client wrapping all backend calls

import type {
	AdminStats,
	DiscoveryResponse,
	EntityLinkOut,
	EntityLinkPage,
	PersonBrief,
	PersonDetail,
	RankMode,
	SearchResponse,
	ShortlistItemOut,
	ShortlistOut,
	ShortlistSummary,
} from "@/types";

// BASE_URL is NEXT_PUBLIC so it can be configured per-environment.
// API_KEY must NOT use the NEXT_PUBLIC_ prefix — it stays server-side only.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_KEY ?? "change-me-in-production";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE_URL}${path}`, {
		...init,
		headers: {
			"X-API-Key": API_KEY,
			"Content-Type": "application/json",
			...init?.headers,
		},
	});

	if (!res.ok) {
		const detail = await res.text().catch(() => res.statusText);
		throw new Error(`API ${res.status}: ${detail}`);
	}

	if (res.status === 204) {
		return undefined as T;
	}

	return res.json() as Promise<T>;
}

export async function searchPersons(
	query: string,
	limit = 20,
): Promise<SearchResponse> {
	const params = new URLSearchParams({ q: query, limit: String(limit) });
	return apiFetch<SearchResponse>(`/search?${params}`);
}

export async function discoverCandidates(
	entityType: string,
	entityId: string,
	mode: RankMode = "standard",
	limit = 20,
	explain = false,
): Promise<DiscoveryResponse> {
	const params = new URLSearchParams({ mode, limit: String(limit) });
	if (explain) params.set("explain", "true");
	return apiFetch<DiscoveryResponse>(
		`/discovery/${entityType}/${entityId}?${params}`,
	);
}

export async function getPerson(personId: string): Promise<PersonDetail> {
	return apiFetch<PersonDetail>(`/person/${personId}`);
}

export async function getPersonBrief(
	personId: string,
	seedText: string,
): Promise<PersonBrief> {
	return apiFetch<PersonBrief>(`/person/${personId}/brief`, {
		method: "POST",
		body: JSON.stringify({ seed_text: seedText }),
	});
}

export async function listShortlists(): Promise<ShortlistSummary[]> {
	return apiFetch<ShortlistSummary[]>("/shortlists");
}

export async function createShortlist(
	name: string,
	description?: string,
): Promise<ShortlistOut> {
	return apiFetch<ShortlistOut>("/shortlists", {
		method: "POST",
		body: JSON.stringify({ name, description }),
	});
}

export async function getShortlist(id: string): Promise<ShortlistOut> {
	return apiFetch<ShortlistOut>(`/shortlists/${id}`);
}

export async function deleteShortlist(id: string): Promise<void> {
	await apiFetch<void>(`/shortlists/${id}`, { method: "DELETE" });
}

export async function addToShortlist(
	shortlistId: string,
	personId: string,
	note?: string,
): Promise<ShortlistItemOut> {
	return apiFetch<ShortlistItemOut>(`/shortlists/${shortlistId}/items`, {
		method: "POST",
		body: JSON.stringify({ person_id: personId, note }),
	});
}

export async function removeFromShortlist(
	shortlistId: string,
	personId: string,
): Promise<void> {
	await apiFetch<void>(`/shortlists/${shortlistId}/items/${personId}`, {
		method: "DELETE",
	});
}

export async function getAdminStats(): Promise<AdminStats> {
	return apiFetch<AdminStats>("/admin/stats");
}

export async function listEntityLinks(
	status = "pending",
	page = 1,
	pageSize = 20,
	signal?: AbortSignal,
): Promise<EntityLinkPage> {
	const params = new URLSearchParams({
		status,
		page: String(page),
		page_size: String(pageSize),
	});
	return apiFetch<EntityLinkPage>(`/admin/entity-links?${params}`, { signal });
}

export async function approveEntityLink(id: string): Promise<EntityLinkOut> {
	return apiFetch<EntityLinkOut>(`/admin/entity-links/${id}/approve`, {
		method: "POST",
	});
}

export async function rejectEntityLink(id: string): Promise<EntityLinkOut> {
	return apiFetch<EntityLinkOut>(`/admin/entity-links/${id}/reject`, {
		method: "POST",
	});
}
