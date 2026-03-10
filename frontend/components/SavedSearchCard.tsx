"use client";

import Link from "next/link";
import type { SavedSearchOut } from "@/types";

interface SavedSearchCardProps {
	search: SavedSearchOut;
	onDelete?: (id: string) => void;
}

export function SavedSearchCard({ search, onDelete }: SavedSearchCardProps) {
	return (
		<div className="bg-white border border-gray-200 rounded-lg p-4 flex items-start justify-between">
			<div className="flex-1 min-w-0">
				<p className="text-sm font-medium text-gray-900 truncate">
					{search.name}
				</p>
				<p className="text-xs text-gray-500 mt-0.5 truncate">{search.query}</p>
				<p className="text-xs text-gray-400 mt-1">
					{new Date(search.created_at).toLocaleDateString()}
					{search.last_run_at && (
						<>
							{" · last run "}
							{new Date(search.last_run_at).toLocaleDateString()}
						</>
					)}
				</p>
			</div>
			<div className="ml-3 flex items-center gap-2 shrink-0">
				<Link
					href={`/?q=${encodeURIComponent(search.query)}`}
					className="text-xs text-blue-600 hover:text-blue-800"
				>
					Run
				</Link>
				{onDelete && (
					<button
						type="button"
						onClick={() => onDelete(search.id)}
						className="text-xs text-red-400 hover:text-red-600"
					>
						Delete
					</button>
				)}
			</div>
		</div>
	);
}
