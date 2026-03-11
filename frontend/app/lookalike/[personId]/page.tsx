import Link from "next/link";
import { AddToShortlistButton } from "@/components/AddToShortlistButton";
import { fetchLookalikes, getPerson } from "@/lib/api";
import type { LookalikeResponse } from "@/types";

interface LookalikePageProps {
	params: Promise<{ personId: string }>;
}

export default async function LookalikePage({ params }: LookalikePageProps) {
	const { personId } = await params;

	let personName = "Unknown";
	let error: string | null = null;
	let data: LookalikeResponse | undefined;

	try {
		const [person, lookalikes] = await Promise.all([
			getPerson(personId),
			fetchLookalikes(personId),
		]);
		personName = person.name;
		data = lookalikes;
	} catch (e) {
		error = e instanceof Error ? e.message : "Failed to load lookalikes";
	}

	if (error) {
		return (
			<main className="min-h-screen bg-gray-50 px-4 py-10">
				<div className="max-w-3xl mx-auto">
					<Link href="/" className="text-blue-600 hover:underline text-sm">
						← Back
					</Link>
					<p className="text-red-500 mt-4">{error}</p>
				</div>
			</main>
		);
	}

	if (!data) return null;

	return (
		<main className="min-h-screen bg-gray-50 px-4 py-10">
			<div className="max-w-3xl mx-auto">
				<div className="flex items-center gap-2 mb-6">
					<Link href="/" className="text-blue-600 hover:underline text-sm">
						← Search
					</Link>
					<span className="text-gray-400">/</span>
					<Link
						href={`/person/${personId}`}
						className="text-blue-600 hover:underline text-sm"
					>
						{personName}
					</Link>
					<span className="text-gray-400">/</span>
					<span className="text-sm text-gray-600">Lookalikes</span>
				</div>

				<h1 className="text-2xl font-bold text-gray-900 mb-1">
					Lookalikes for {personName}
				</h1>
				<p className="text-sm text-gray-500 mb-6">
					People with similar research profiles and expertise
				</p>

				{data.results.length === 0 ? (
					<div className="bg-white border border-gray-200 rounded-lg p-6 text-center text-gray-500">
						No similar people found. This person may not have an embedding yet.
					</div>
				) : (
					<div className="space-y-3">
						{data.results.map((result, idx) => {
							const pct = Math.round(result.similarity * 100);
							return (
								<div
									key={result.id}
									className="bg-white border border-gray-200 rounded-lg p-4"
								>
									<div className="flex items-center justify-between mb-2">
										<div className="flex items-center gap-3">
											<span className="text-xs font-mono text-gray-400 w-6">
												#{idx + 1}
											</span>
											<Link
												href={`/person/${result.id}`}
												className="font-medium text-gray-900 hover:text-blue-600"
											>
												{result.name}
											</Link>
										</div>
										<div className="flex items-center gap-2">
											<Link
												href={`/graph/person/${result.id}`}
												className="px-2.5 py-1 bg-purple-50 text-purple-700 rounded text-xs font-medium hover:bg-purple-100"
											>
												View Graph
											</Link>
											<AddToShortlistButton personId={result.id} />
										</div>
									</div>
									{/* Similarity bar */}
									<div className="flex items-center gap-3">
										<div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
											<div
												className="h-full bg-blue-500 rounded-full transition-all"
												style={{ width: `${pct}%` }}
											/>
										</div>
										<span className="text-sm font-medium text-gray-600 w-12 text-right">
											{pct}%
										</span>
									</div>
								</div>
							);
						})}
					</div>
				)}
			</div>
		</main>
	);
}
