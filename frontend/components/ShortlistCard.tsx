"use client";

import Link from "next/link";
import type { ShortlistSummary } from "@/types";

interface ShortlistCardProps {
	shortlist: ShortlistSummary;
	onDelete?: (id: string) => void;
}

export function ShortlistCard({ shortlist, onDelete }: ShortlistCardProps) {
	return (
		<div className="bg-white border border-gray-200 rounded-lg p-4 flex items-start justify-between">
			<div className="flex-1 min-w-0">
				<Link
					href={`/shortlists/${shortlist.id}`}
					className="text-blue-700 font-medium hover:underline text-sm"
				>
					{shortlist.name}
				</Link>
				{shortlist.description && (
					<p className="text-xs text-gray-500 mt-0.5 truncate">
						{shortlist.description}
					</p>
				)}
				<p className="text-xs text-gray-400 mt-1">
					{shortlist.item_count} candidate{shortlist.item_count !== 1 ? "s" : ""}
					{" · "}
					{new Date(shortlist.created_at).toLocaleDateString()}
				</p>
			</div>
			{onDelete && (
				<button
					type="button"
					onClick={() => onDelete(shortlist.id)}
					className="ml-3 text-xs text-red-400 hover:text-red-600 shrink-0"
				>
					Delete
				</button>
			)}
		</div>
	);
}
