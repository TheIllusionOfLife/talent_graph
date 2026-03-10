"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SavedSearchCard } from "@/components/SavedSearchCard";
import { deleteSavedSearch, listSavedSearches } from "@/lib/api";
import type { SavedSearchOut } from "@/types";

export default function SavedSearchesPage() {
	const [searches, setSearches] = useState<SavedSearchOut[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		listSavedSearches()
			.then(setSearches)
			.catch((e: unknown) =>
				setError(e instanceof Error ? e.message : "Load failed"),
			)
			.finally(() => setLoading(false));
	}, []);

	async function handleDelete(id: string) {
		try {
			await deleteSavedSearch(id);
			setSearches((prev) => prev.filter((s) => s.id !== id));
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Delete failed");
		}
	}

	return (
		<main className="min-h-screen bg-gray-50 px-4 py-10">
			<div className="max-w-2xl mx-auto">
				<div className="flex items-center gap-2 mb-6">
					<Link href="/" className="text-blue-600 hover:underline text-sm">
						← Search
					</Link>
					<span className="text-gray-400">/</span>
					<span className="text-sm text-gray-600">Saved Searches</span>
				</div>

				<h1 className="text-2xl font-bold text-gray-900 mb-6">
					Saved Searches
				</h1>

				{error && <p className="text-red-500 text-sm mb-4">{error}</p>}

				{loading ? (
					<div className="space-y-3">
						{[1, 2, 3].map((i) => (
							<div
								key={i}
								className="h-16 bg-gray-200 rounded-lg animate-pulse"
							/>
						))}
					</div>
				) : searches.length === 0 ? (
					<p className="text-gray-400 text-sm text-center py-10">
						No saved searches yet. Run a search and click Save to store it.
					</p>
				) : (
					<div className="space-y-3">
						{searches.map((s) => (
							<SavedSearchCard key={s.id} search={s} onDelete={handleDelete} />
						))}
					</div>
				)}
			</div>
		</main>
	);
}
