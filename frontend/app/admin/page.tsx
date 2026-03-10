"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAdminStats } from "@/lib/api";
import type { AdminStats } from "@/types";

export default function AdminPage() {
	const [stats, setStats] = useState<AdminStats | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		getAdminStats()
			.then(setStats)
			.catch((e: unknown) =>
				setError(e instanceof Error ? e.message : "Failed to load stats"),
			)
			.finally(() => setLoading(false));
	}, []);

	return (
		<main className="max-w-3xl mx-auto px-4 py-8">
			<div className="flex items-center justify-between mb-6">
				<h1 className="text-2xl font-bold">Admin Dashboard</h1>
				<Link href="/" className="text-sm text-blue-600 hover:underline">
					← Back to search
				</Link>
			</div>

			{loading && <p className="text-gray-500">Loading stats…</p>}
			{error && (
				<p className="text-red-600 bg-red-50 border border-red-200 rounded p-3">
					{error}
				</p>
			)}

			{stats && (
				<>
					<section className="mb-8">
						<h2 className="text-lg font-semibold mb-3">System Overview</h2>
						<div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
							<StatCard label="Persons" value={stats.person_count} />
							<StatCard label="Papers" value={stats.paper_count} />
							<StatCard label="Repos" value={stats.repo_count} />
							<StatCard
								label="Pending Links"
								value={stats.pending_entity_links}
								highlight={stats.pending_entity_links > 0}
							/>
						</div>
					</section>

					<section>
						<h2 className="text-lg font-semibold mb-3">Actions</h2>
						<ul className="space-y-2">
							<li>
								<Link
									href="/admin/entity-review"
									className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
								>
									Review Entity Links
									{stats.pending_entity_links > 0 && (
										<span className="bg-white text-blue-700 rounded-full px-2 text-xs font-bold">
											{stats.pending_entity_links}
										</span>
									)}
								</Link>
							</li>
							<li>
								<Link
									href="/shortlists"
									className="inline-block px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 text-sm"
								>
									Manage Shortlists
								</Link>
							</li>
						</ul>
					</section>
				</>
			)}
		</main>
	);
}

function StatCard({
	label,
	value,
	highlight = false,
}: {
	label: string;
	value: number;
	highlight?: boolean;
}) {
	return (
		<div
			className={`rounded border p-4 text-center ${highlight ? "border-amber-400 bg-amber-50" : "border-gray-200 bg-white"}`}
		>
			<div className="text-2xl font-bold">{value.toLocaleString()}</div>
			<div className="text-xs text-gray-500 mt-1">{label}</div>
		</div>
	);
}
