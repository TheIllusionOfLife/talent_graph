// API client wrapping all backend calls

import type {
	DiscoveryResponse,
	PersonDetail,
	RankMode,
	SearchResponse,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "change-me-in-production";

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
): Promise<DiscoveryResponse> {
	const params = new URLSearchParams({ mode, limit: String(limit) });
	return apiFetch<DiscoveryResponse>(
		`/discovery/${entityType}/${entityId}?${params}`,
	);
}

export async function getPerson(personId: string): Promise<PersonDetail> {
	return apiFetch<PersonDetail>(`/person/${personId}`);
}
