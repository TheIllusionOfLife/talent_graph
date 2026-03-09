import Link from "next/link";
import { CandidateCard } from "@/components/CandidateCard";
import { discoverCandidates } from "@/lib/api";
import type { DiscoveryResponse, RankMode } from "@/types";

interface DiscoveryPageProps {
	params: Promise<{ entityType: string; entityId: string }>;
	searchParams: Promise<{ mode?: string }>;
}

const MODES: RankMode[] = ["standard", "hidden", "emerging"];

const MODE_DESCRIPTIONS: Record<RankMode, string> = {
	standard: "Balanced ranking across all signals",
	hidden:
		"Amplifies novelty and cross-source evidence — surfaces hidden experts",
	emerging: "Amplifies recent growth — surfaces rising researchers",
};

export default async function DiscoveryPage({
	params,
	searchParams,
}: DiscoveryPageProps) {
	const { entityType, entityId } = await params;
	const { mode: rawMode } = await searchParams;
	const mode: RankMode = MODES.includes(rawMode as RankMode)
		? (rawMode as RankMode)
		: "standard";

	let data: DiscoveryResponse | undefined;
	let error: string | null = null;

	try {
		data = await discoverCandidates(entityType, entityId, mode, 20);
	} catch (e) {
		error = e instanceof Error ? e.message : "Unknown error";
	}

	return (
		<main className="min-h-screen bg-gray-50 px-4 py-10">
			<div className="max-w-3xl mx-auto">
				<div className="flex items-center gap-2 mb-6">
					<Link href="/" className="text-blue-600 hover:underline text-sm">
						← Search
					</Link>
					<span className="text-gray-400">/</span>
					<span className="text-sm text-gray-600 capitalize">
						{entityType} · {entityId.slice(0, 12)}…
					</span>
				</div>

				<h1 className="text-2xl font-bold text-gray-900 mb-1">
					Discovery: {entityType}
				</h1>
				<p className="text-sm text-gray-500 mb-6">{MODE_DESCRIPTIONS[mode]}</p>

				{/* Mode toggle */}
				<div className="flex gap-2 mb-6">
					{MODES.map((m) => (
						<Link
							key={m}
							href={`/discovery/${entityType}/${entityId}?mode=${m}`}
							className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
								m === mode
									? "bg-blue-600 text-white"
									: "bg-white border border-gray-200 text-gray-600 hover:bg-gray-50"
							}`}
						>
							{m.charAt(0).toUpperCase() + m.slice(1)}
						</Link>
					))}
				</div>

				{error && (
					<p className="text-red-500 text-sm">Failed to load: {error}</p>
				)}

				{data && data.candidates.length === 0 && (
					<p className="text-gray-500 text-sm">
						No candidates found. Try seeding more data first.
					</p>
				)}

				{data && data.candidates.length > 0 && (
					<div className="space-y-3">
						{data.candidates.map((candidate) => (
							<CandidateCard key={candidate.id} candidate={candidate} />
						))}
					</div>
				)}
			</div>
		</main>
	);
}
