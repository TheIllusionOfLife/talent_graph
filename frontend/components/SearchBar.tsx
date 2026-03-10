"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createSavedSearch } from "@/lib/api";

interface SearchBarProps {
	initialQuery?: string;
}

export function SearchBar({ initialQuery = "" }: SearchBarProps) {
	const router = useRouter();
	const [query, setQuery] = useState(initialQuery);
	const [saving, setSaving] = useState(false);
	const [saveName, setSaveName] = useState("");
	const [saveError, setSaveError] = useState<string | null>(null);
	const [saved, setSaved] = useState(false);

	function handleSubmit(e: React.FormEvent) {
		e.preventDefault();
		const q = query.trim();
		if (!q) return;
		setSaving(false);
		setSaved(false);
		router.push(`/?q=${encodeURIComponent(q)}`);
	}

	async function handleSave(e: React.FormEvent) {
		e.preventDefault();
		const name = saveName.trim();
		const q = query.trim();
		if (!name || !q) return;
		setSaveError(null);
		try {
			await createSavedSearch(name, q);
			setSaving(false);
			setSaveName("");
			setSaved(true);
		} catch (err: unknown) {
			setSaveError(err instanceof Error ? err.message : "Save failed");
		}
	}

	return (
		<div className="w-full max-w-2xl">
			<form onSubmit={handleSubmit} className="flex gap-2">
				<input
					type="text"
					value={query}
					onChange={(e) => {
						setQuery(e.target.value);
						setSaved(false);
					}}
					placeholder="Search for researchers, topics, or papers…"
					className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
				/>
				<button
					type="submit"
					className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
				>
					Search
				</button>
				{query.trim() && (
					<button
						type="button"
						onClick={() => {
							setSaving((v) => !v);
							setSaveError(null);
						}}
						className="px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors"
						title="Save search"
					>
						{saved ? "✓ Saved" : "Save"}
					</button>
				)}
			</form>

			{saving && (
				<form onSubmit={handleSave} className="mt-2 flex gap-2 items-center">
					<input
						type="text"
						value={saveName}
						onChange={(e) => setSaveName(e.target.value)}
						placeholder="Name this search…"
						className="flex-1 px-3 py-1.5 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
					<button
						type="submit"
						disabled={!saveName.trim()}
						className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
					>
						Save
					</button>
					<button
						type="button"
						onClick={() => {
							setSaving(false);
							setSaveError(null);
						}}
						className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
					>
						Cancel
					</button>
					{saveError && (
						<span className="text-xs text-red-500">{saveError}</span>
					)}
				</form>
			)}
		</div>
	);
}
