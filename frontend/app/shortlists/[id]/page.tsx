"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
	getShortlist,
	removeFromShortlist,
	updateShortlistItem,
} from "@/lib/api";
import type { ShortlistOut } from "@/types";

export default function ShortlistDetailPage() {
	const params = useParams<{ id: string }>();
	const [shortlist, setShortlist] = useState<ShortlistOut | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [editingNote, setEditingNote] = useState<string | null>(null);
	const [noteInput, setNoteInput] = useState("");
	const [savingNote, setSavingNote] = useState(false);
	const [showExport, setShowExport] = useState(false);

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

	async function handleSaveNote(personId: string) {
		if (!shortlist) return;
		setSavingNote(true);
		try {
			const updated = await updateShortlistItem(shortlist.id, personId, {
				note: noteInput || null,
			});
			setShortlist((prev) =>
				prev
					? {
							...prev,
							items: prev.items.map((item) =>
								item.person_id === personId
									? { ...item, note: updated.note }
									: item,
							),
						}
					: null,
			);
			setEditingNote(null);
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Save failed");
		} finally {
			setSavingNote(false);
		}
	}

	async function handleMovePosition(personId: string, delta: number) {
		if (!shortlist) return;
		const item = shortlist.items.find((i) => i.person_id === personId);
		if (!item) return;
		const newPos = Math.max(0, item.position + delta);
		try {
			const updated = await updateShortlistItem(shortlist.id, personId, {
				position: newPos,
			});
			setShortlist((prev) =>
				prev
					? {
							...prev,
							items: prev.items.map((i) =>
								i.person_id === personId
									? { ...i, position: updated.position }
									: i,
							),
						}
					: null,
			);
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Move failed");
		}
	}

	function sanitizeFilename(name: string) {
		return name.replace(/[/\\:*?"<>|\n\r]/g, "_").trim() || "shortlist";
	}

	function handleExport(format: "csv" | "json") {
		if (!shortlist) return;
		let content: string;
		let mimeType: string;
		let filename: string;

		if (format === "csv") {
			const header = "Position,Name,GitHub,OpenAlex ID,Note,Added At";
			const rows = shortlist.items
				.sort((a, b) => a.position - b.position)
				.map((item) => {
					const name = `"${(item.person?.name ?? item.person_id).replace(/"/g, '""')}"`;
					const github = item.person?.github_login ?? "";
					const openalex = item.person?.openalex_author_id ?? "";
					const note = `"${(item.note ?? "").replace(/"/g, '""')}"`;
					const addedAt = item.added_at;
					return `${item.position},${name},${github},${openalex},${note},${addedAt}`;
				});
			content = [header, ...rows].join("\n");
			mimeType = "text/csv";
			filename = `${sanitizeFilename(shortlist.name)}.csv`;
		} else {
			content = JSON.stringify(shortlist, null, 2);
			mimeType = "application/json";
			filename = `${sanitizeFilename(shortlist.name)}.json`;
		}

		const blob = new Blob([content], { type: mimeType });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = filename;
		a.click();
		URL.revokeObjectURL(url);
		setShowExport(false);
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

	if (error && !shortlist) {
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

	if (!shortlist) return null;

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

				<div className="flex items-start justify-between mb-6">
					<div>
						<h1 className="text-2xl font-bold text-gray-900">
							{shortlist.name}
						</h1>
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
					{shortlist.items.length > 0 && (
						<div className="relative">
							<button
								type="button"
								onClick={() => setShowExport((v) => !v)}
								className="text-xs px-3 py-1.5 border border-gray-200 rounded hover:bg-gray-50 text-gray-600"
							>
								Export
							</button>
							{showExport && (
								<div className="absolute right-0 top-8 z-10 bg-white border border-gray-200 rounded shadow-md min-w-28">
									<button
										type="button"
										onClick={() => handleExport("csv")}
										className="w-full text-left text-xs px-3 py-2 hover:bg-gray-50 text-gray-700"
									>
										CSV
									</button>
									<button
										type="button"
										onClick={() => handleExport("json")}
										className="w-full text-left text-xs px-3 py-2 hover:bg-gray-50 text-gray-700"
									>
										JSON
									</button>
								</div>
							)}
						</div>
					)}
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
									<div className="flex items-start gap-2 flex-1 min-w-0">
										<div className="flex flex-col gap-0.5 shrink-0">
											<button
												type="button"
												onClick={() => handleMovePosition(item.person_id, -1)}
												className="text-xs text-gray-400 hover:text-gray-600 leading-none"
												title="Move up"
											>
												▲
											</button>
											<span className="text-xs text-gray-300 text-center">
												{item.position}
											</span>
											<button
												type="button"
												onClick={() => handleMovePosition(item.person_id, 1)}
												className="text-xs text-gray-400 hover:text-gray-600 leading-none"
												title="Move down"
											>
												▼
											</button>
										</div>
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
											{editingNote === item.person_id ? (
												<div className="flex items-center gap-1 mt-1">
													<input
														type="text"
														value={noteInput}
														onChange={(e) => setNoteInput(e.target.value)}
														className="text-xs border border-gray-200 rounded px-2 py-1 flex-1"
														placeholder="Add a note…"
													/>
													<button
														type="button"
														disabled={savingNote}
														onClick={() => handleSaveNote(item.person_id)}
														className="text-xs text-blue-500 hover:underline disabled:text-gray-400"
													>
														{savingNote ? "…" : "Save"}
													</button>
													<button
														type="button"
														onClick={() => setEditingNote(null)}
														className="text-xs text-gray-400 hover:text-gray-600"
													>
														Cancel
													</button>
												</div>
											) : (
												<div className="flex items-center gap-1 mt-0.5">
													{item.note ? (
														<p className="text-xs text-gray-500">{item.note}</p>
													) : (
														<p className="text-xs text-gray-300 italic">
															No note
														</p>
													)}
													<button
														type="button"
														onClick={() => {
															setEditingNote(item.person_id);
															setNoteInput(item.note ?? "");
														}}
														className="text-xs text-gray-400 hover:text-gray-600"
														title="Edit note"
													>
														✏
													</button>
												</div>
											)}
											<p className="text-xs text-gray-400 mt-1">
												Added {new Date(item.added_at).toLocaleDateString()}
											</p>
										</div>
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
