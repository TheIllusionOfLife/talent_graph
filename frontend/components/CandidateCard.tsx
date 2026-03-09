import Link from "next/link";
import type { CandidateResult } from "@/types";

interface CandidateCardProps {
	candidate: CandidateResult;
}

const SIGNAL_LABELS: Record<string, string> = {
	semantic_similarity: "Semantic",
	graph_proximity: "Graph",
	novelty: "Novelty",
	growth: "Growth",
	evidence_quality: "Evidence",
	credibility: "Credibility",
};

function ScoreBar({ value }: { value: number }) {
	const pct = Math.round(value * 100);
	return (
		<div className="flex items-center gap-2">
			<div className="flex-1 bg-gray-100 rounded-full h-1.5">
				<div
					className="bg-blue-500 h-1.5 rounded-full"
					style={{ width: `${pct}%` }}
				/>
			</div>
			<span className="text-xs text-gray-500 w-8 text-right">{pct}%</span>
		</div>
	);
}

export function CandidateCard({ candidate }: CandidateCardProps) {
	return (
		<div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
			<div className="flex items-start justify-between mb-3">
				<div>
					<Link
						href={`/person/${candidate.id}`}
						className="text-blue-700 font-semibold hover:underline"
					>
						{candidate.name}
					</Link>
					<p className="text-xs text-gray-400 mt-0.5">
						{candidate.hop_distance}-hop · Score: {candidate.score.toFixed(3)}
					</p>
				</div>
				<span className="text-lg font-bold text-blue-700">
					{Math.round(candidate.score * 100)}
				</span>
			</div>

			<div className="space-y-1.5">
				{Object.entries(candidate.breakdown).map(([key, val]) => (
					<div key={key} className="flex items-center gap-2">
						<span className="text-xs text-gray-500 w-20 shrink-0">
							{SIGNAL_LABELS[key] ?? key}
						</span>
						<ScoreBar value={val as number} />
					</div>
				))}
			</div>
		</div>
	);
}
