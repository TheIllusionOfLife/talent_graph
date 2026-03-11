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
		<main className="min-h-screen bg-gray-50 flex flex-col items-center pt-20 px-4">
			<h1 className="text-4xl font-extrabold text-gray-900 mb-3 tracking-tight">
				Talent Graph
			</h1>
			<p className="text-gray-600 text-base mb-2 max-w-lg text-center">
				Find exceptional people who don't appear in traditional searches.
			</p>
			<p className="text-gray-400 text-sm mb-8 max-w-md text-center">
				Explore research networks, coauthor chains, and shared organizations to
				discover hidden experts and emerging talent.
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
