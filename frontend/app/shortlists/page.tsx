"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { createShortlist, deleteShortlist, listShortlists } from "@/lib/api";
import { ShortlistCard } from "@/components/ShortlistCard";
import type { ShortlistSummary } from "@/types";

export default function ShortlistsPage() {
	const [shortlists, setShortlists] = useState<ShortlistSummary[]>([]);
	const [loading, setLoading] = useState(true);
	const [creating, setCreating] = useState(false);
	const [newName, setNewName] = useState("");
	const [newDesc, setNewDesc] = useState("");
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		listShortlists()
			.then(setShortlists)
			.catch((e: unknown) => setError(e instanceof Error ? e.message : "Load failed"))
			.finally(() => setLoading(false));
	}, []);

	async function handleCreate(e: React.FormEvent) {
		e.preventDefault();
		if (!newName.trim()) return;
		setCreating(true);
		try {
			await createShortlist(newName.trim(), newDesc.trim() || undefined);
			setNewName("");
			setNewDesc("");
			const updated = await listShortlists();
			setShortlists(updated);
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Create failed");
		} finally {
			setCreating(false);
		}
	}

	async function handleDelete(id: string) {
		try {
			await deleteShortlist(id);
			setShortlists((prev) => prev.filter((s) => s.id !== id));
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
					<span className="text-sm text-gray-600">Shortlists</span>
				</div>

				<h1 className="text-2xl font-bold text-gray-900 mb-6">Shortlists</h1>

				{/* Create form */}
				<form
					onSubmit={handleCreate}
					className="bg-white border border-gray-200 rounded-lg p-4 mb-6"
				>
					<h2 className="text-sm font-semibold text-gray-700 mb-3">
						New Shortlist
					</h2>
					<div className="flex gap-2">
						<input
							type="text"
							value={newName}
							onChange={(e) => setNewName(e.target.value)}
							placeholder="Shortlist name"
							className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
							required
						/>
						<input
							type="text"
							value={newDesc}
							onChange={(e) => setNewDesc(e.target.value)}
							placeholder="Description (optional)"
							className="flex-1 border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
						/>
						<button
							type="submit"
							disabled={creating || !newName.trim()}
							className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
						>
							{creating ? "Creating…" : "Create"}
						</button>
					</div>
				</form>

				{error && (
					<p className="text-red-500 text-sm mb-4">{error}</p>
				)}

				{loading ? (
					<div className="space-y-3">
						{[1, 2, 3].map((i) => (
							<div key={i} className="h-16 bg-gray-200 rounded-lg animate-pulse" />
						))}
					</div>
				) : shortlists.length === 0 ? (
					<p className="text-gray-400 text-sm text-center py-10">
						No shortlists yet. Create one above.
					</p>
				) : (
					<div className="space-y-3">
						{shortlists.map((sl) => (
							<ShortlistCard
								key={sl.id}
								shortlist={sl}
								onDelete={handleDelete}
							/>
						))}
					</div>
				)}
			</div>
		</main>
	);
}
