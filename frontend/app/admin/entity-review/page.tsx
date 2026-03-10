"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
	approveEntityLink,
	listEntityLinks,
	rejectEntityLink,
} from "@/lib/api";
import type { EntityLinkOut, EntityLinkPage } from "@/types";

export default function EntityReviewPage() {
	const [page, setPage] = useState<EntityLinkPage | null>(null);
	const [currentPage, setCurrentPage] = useState(1);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [processing, setProcessing] = useState<string | null>(null);
	const controllerRef = useRef<AbortController | null>(null);

	const load = useCallback((p: number) => {
		// Abort any in-flight request to avoid stale results from earlier responses
		controllerRef.current?.abort();
		const controller = new AbortController();
		controllerRef.current = controller;

		setLoading(true);
		setError(null);
		listEntityLinks("pending", p, 20, controller.signal)
			.then((data) => {
				setPage(data);
				setCurrentPage(p);
			})
			.catch((e: unknown) => {
				if (e instanceof Error && e.name === "AbortError") return;
				setError(
					e instanceof Error ? e.message : "Failed to load entity links",
				);
			})
			.finally(() => setLoading(false));
	}, []);

	useEffect(() => {
		load(1);
		return () => {
			controllerRef.current?.abort();
		};
	}, [load]);

	async function handleAction(
		link: EntityLinkOut,
		action: "approve" | "reject",
	) {
		setProcessing(link.id);
		try {
			if (action === "approve") {
				await approveEntityLink(link.id);
			} else {
				await rejectEntityLink(link.id);
			}
			// If we just resolved the last item on this page, go to previous page
			const nextPage =
				page?.items.length === 1 && currentPage > 1
					? currentPage - 1
					: currentPage;
			load(nextPage);
		} catch (e: unknown) {
			setError(e instanceof Error ? e.message : "Action failed");
		} finally {
			setProcessing(null);
		}
	}

	const totalPages = page ? Math.ceil(page.total / page.page_size) : 1;

	return (
		<main className="max-w-4xl mx-auto px-4 py-8">
			<div className="flex items-center justify-between mb-6">
				<h1 className="text-2xl font-bold">Entity Resolution Review</h1>
				<Link href="/admin" className="text-sm text-blue-600 hover:underline">
					← Admin dashboard
				</Link>
			</div>

			{error && (
				<div className="flex items-center justify-between bg-red-50 border border-red-200 rounded p-3 mb-4">
					<p className="text-red-600">{error}</p>
					<button
						type="button"
						onClick={() => {
							setError(null);
							load(currentPage);
						}}
						className="ml-4 text-sm text-red-700 underline hover:no-underline shrink-0"
					>
						Retry
					</button>
				</div>
			)}

			{loading && <p className="text-gray-500">Loading…</p>}

			{!loading && page && page.items.length === 0 && (
				<p className="text-gray-500 italic">
					No pending entity links to review.
				</p>
			)}

			{!loading && page && page.items.length > 0 && (
				<>
					<p className="text-sm text-gray-500 mb-4">
						{page.total} pending link{page.total !== 1 ? "s" : ""}
					</p>

					<div className="space-y-3">
						{page.items.map((link) => (
							<EntityLinkRow
								key={link.id}
								link={link}
								busy={processing === link.id}
								onAction={handleAction}
							/>
						))}
					</div>

					{totalPages > 1 && (
						<div className="flex gap-2 mt-6 items-center">
							<button
								type="button"
								disabled={currentPage <= 1}
								onClick={() => load(currentPage - 1)}
								className="px-3 py-1 border rounded text-sm disabled:opacity-40"
							>
								← Prev
							</button>
							<span className="text-sm text-gray-600">
								Page {currentPage} of {totalPages}
							</span>
							<button
								type="button"
								disabled={currentPage >= totalPages}
								onClick={() => load(currentPage + 1)}
								className="px-3 py-1 border rounded text-sm disabled:opacity-40"
							>
								Next →
							</button>
						</div>
					)}
				</>
			)}
		</main>
	);
}

function EntityLinkRow({
	link,
	busy,
	onAction,
}: {
	link: EntityLinkOut;
	busy: boolean;
	onAction: (link: EntityLinkOut, action: "approve" | "reject") => void;
}) {
	return (
		<div className="border border-gray-200 rounded p-4 flex flex-col sm:flex-row sm:items-center gap-3">
			<div className="flex-1 text-sm space-y-1">
				<div className="font-mono text-xs text-gray-400">
					{link.person_id_a} ↔ {link.person_id_b}
				</div>
				<div className="flex gap-4 text-gray-600">
					<span>
						Confidence: <strong>{(link.confidence * 100).toFixed(1)}%</strong>
					</span>
					<span>Method: {link.method}</span>
				</div>
				<div className="text-gray-400 text-xs">
					Created {new Date(link.created_at).toLocaleDateString()}
				</div>
			</div>
			<div className="flex gap-2 shrink-0">
				<button
					type="button"
					disabled={busy}
					aria-busy={busy}
					aria-label={busy ? "Approving…" : "Approve"}
					onClick={() => onAction(link, "approve")}
					className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
				>
					{busy ? "…" : "Approve"}
				</button>
				<button
					type="button"
					disabled={busy}
					aria-busy={busy}
					aria-label={busy ? "Rejecting…" : "Reject"}
					onClick={() => onAction(link, "reject")}
					className="px-3 py-1.5 bg-red-100 text-red-700 border border-red-300 text-sm rounded hover:bg-red-200 disabled:opacity-50"
				>
					{busy ? "…" : "Reject"}
				</button>
			</div>
		</div>
	);
}
