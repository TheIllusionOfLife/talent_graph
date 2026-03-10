import Link from "next/link";
import type { SearchResult } from "@/types";

interface SearchResultsProps {
	results: SearchResult[];
	query: string;
}

export function SearchResults({ results, query }: SearchResultsProps) {
	if (results.length === 0) {
		return (
			<p className="text-gray-500 text-sm mt-4">
				No results for{" "}
				<span className="font-medium">&ldquo;{query}&rdquo;</span>
			</p>
		);
	}

	return (
		<div className="w-full max-w-2xl mt-6 space-y-3">
			<p className="text-sm text-gray-500">
				{results.length} result{results.length !== 1 ? "s" : ""} for{" "}
				<span className="font-medium">&ldquo;{query}&rdquo;</span>
			</p>
			{results.map((r) => (
				<div
					key={r.id}
					className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:shadow-sm transition-shadow"
				>
					<div>
						<Link
							href={`/person/${r.id}`}
							className="text-blue-700 font-medium hover:underline"
						>
							{r.name}
						</Link>
					</div>
					<div className="flex items-center gap-3 text-sm text-gray-500">
						<span>Score: {r.score.toFixed(3)}</span>
						<Link
							href={`/discovery/person/${r.id}`}
							className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-xs"
						>
							Discover similar →
						</Link>
					</div>
				</div>
			))}
		</div>
	);
}
