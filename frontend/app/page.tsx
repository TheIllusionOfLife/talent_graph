import { Suspense } from "react";
import { SearchBar } from "@/components/SearchBar";
import { SearchResults } from "@/components/SearchResults";
import { searchPersons } from "@/lib/api";

interface HomeProps {
	searchParams: Promise<{ q?: string }>;
}

async function Results({ query }: { query: string }) {
	try {
		const data = await searchPersons(query, 20);
		return <SearchResults results={data.results} query={query} />;
	} catch {
		return (
			<p className="text-red-500 text-sm mt-4">
				Search failed. Is the API server running?
			</p>
		);
	}
}

export default async function Home({ searchParams }: HomeProps) {
	const { q } = await searchParams;
	const query = q?.trim() ?? "";

	return (
		<main className="min-h-screen bg-gray-50 flex flex-col items-center pt-24 px-4">
			<h1 className="text-3xl font-bold text-gray-900 mb-2">Talent Graph</h1>
			<p className="text-gray-500 text-sm mb-8">
				Discover hidden experts using knowledge graphs and embeddings
			</p>

			<SearchBar initialQuery={query} />

			{query && (
				<Suspense
					fallback={<p className="text-gray-400 text-sm mt-6">Searching…</p>}
				>
					<Results query={query} />
				</Suspense>
			)}
		</main>
	);
}
