"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

interface SearchBarProps {
	initialQuery?: string;
}

export function SearchBar({ initialQuery = "" }: SearchBarProps) {
	const router = useRouter();
	const [query, setQuery] = useState(initialQuery);

	function handleSubmit(e: React.FormEvent) {
		e.preventDefault();
		const q = query.trim();
		if (!q) return;
		router.push(`/?q=${encodeURIComponent(q)}`);
	}

	return (
		<form onSubmit={handleSubmit} className="flex gap-2 w-full max-w-2xl">
			<input
				type="text"
				value={query}
				onChange={(e) => setQuery(e.target.value)}
				placeholder="Search for researchers, topics, or papers…"
				className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
			/>
			<button
				type="submit"
				className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
			>
				Search
			</button>
		</form>
	);
}
