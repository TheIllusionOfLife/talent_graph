"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getShortlist, removeFromShortlist } from "@/lib/api";
import type { ShortlistOut } from "@/types";

export default function ShortlistDetailPage() {
	const params = useParams<{ id: string }>();
	const [shortlist, setShortlist] = useState<ShortlistOut | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!params.id) return;
		getShortlist(params.id)
			.then(setShortlist)
			.catch((e: unknown) =>
				setError(e instanceof Error ? e.message : "Load failed"),
			)
			.finally(() => setLoading(false));
	}, [params.id]);

	async function handleRemove(personId: string) {
		if (!shortlist) return;
		try {
			await removeFromShortlist(shortlist.id, personId);
			setShortlist((prev) =>
				prev
					? {
							...prev,
							items: prev.items.filter((item) => item.person_id !== personId),
						}
					: null,
			);
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Remove failed");
		}
	}

	if (loading) {
		return (
			<main className="min-h-screen bg-gray-50 px-4 py-10">
				<div className="max-w-2xl mx-auto space-y-3">
					<div className="h-8 bg-gray-200 rounded animate-pulse w-1/3" />
					{[1, 2, 3].map((i) => (
						<div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
					))}
				</div>
			</main>
		);
	}

	if (error || !shortlist) {
		return (
			<main className="min-h-screen bg-gray-50 px-4 py-10">
				<div className="max-w-2xl mx-auto">
					<Link
						href="/shortlists"
						className="text-blue-600 hover:underline text-sm"
					>
						← Shortlists
					</Link>
					<p className="text-red-500 mt-4">{error ?? "Shortlist not found"}</p>
				</div>
			</main>
		);
	}

	return (
		<main className="min-h-screen bg-gray-50 px-4 py-10">
			<div className="max-w-2xl mx-auto">
				<div className="flex items-center gap-2 mb-6">
					<Link
						href="/shortlists"
						className="text-blue-600 hover:underline text-sm"
					>
						← Shortlists
					</Link>
					<span className="text-gray-400">/</span>
					<span className="text-sm text-gray-600">{shortlist.name}</span>
				</div>

				<div className="mb-6">
					<h1 className="text-2xl font-bold text-gray-900">{shortlist.name}</h1>
					{shortlist.description && (
						<p className="text-gray-500 text-sm mt-1">
							{shortlist.description}
						</p>
					)}
					<p className="text-xs text-gray-400 mt-1">
						{shortlist.items.length} candidate
						{shortlist.items.length !== 1 ? "s" : ""}
					</p>
				</div>

				{error && <p className="text-red-500 text-sm mb-4">{error}</p>}

				{shortlist.items.length === 0 ? (
					<p className="text-gray-400 text-sm text-center py-10">
						No candidates yet. Add some from search or discovery results.
					</p>
				) : (
					<div className="space-y-3">
						{shortlist.items
							.sort((a, b) => a.position - b.position)
							.map((item) => (
								<div
									key={item.person_id}
									className="bg-white border border-gray-200 rounded-lg p-4 flex items-start justify-between"
								>
									<div className="flex-1 min-w-0">
										{item.person ? (
											<Link
												href={`/person/${item.person.id}`}
												className="text-blue-700 font-medium hover:underline text-sm"
											>
												{item.person.name}
											</Link>
										) : (
											<span className="text-sm text-gray-700">
												{item.person_id}
											</span>
										)}
										{item.note && (
											<p className="text-xs text-gray-500 mt-0.5">
												{item.note}
											</p>
										)}
										<p className="text-xs text-gray-400 mt-1">
											Added {new Date(item.added_at).toLocaleDateString()}
										</p>
									</div>
									<div className="flex items-center gap-3 ml-3 shrink-0">
										{item.person && (
											<Link
												href={`/discovery/person/${item.person.id}`}
												className="text-xs text-blue-500 hover:underline"
											>
												Discover
											</Link>
										)}
										<button
											type="button"
											onClick={() => handleRemove(item.person_id)}
											className="text-xs text-red-400 hover:text-red-600"
										>
											Remove
										</button>
									</div>
								</div>
							))}
					</div>
				)}
			</div>
		</main>
	);
}
