"use client";

import { useState } from "react";
import { CandidateCard } from "@/components/CandidateCard";
import type { CandidateResult } from "@/types";

interface DiscoveryResultsProps {
	candidates: CandidateResult[];
	seedText?: string;
}

export function DiscoveryResults({
	candidates,
	seedText,
}: DiscoveryResultsProps) {
	const [minScorePct, setMinScorePct] = useState(0);
	const filtered = candidates.filter((c) => c.score >= minScorePct / 100);

	return (
		<div>
			<div className="flex items-center gap-3 mb-4">
				<label htmlFor="score-filter" className="text-xs text-gray-500">
					Min score
				</label>
				<input
					id="score-filter"
					type="range"
					min={0}
					max={100}
					step={5}
					value={minScorePct}
					onChange={(e) => setMinScorePct(Number(e.target.value))}
					className="flex-1"
				/>
				<span className="text-xs text-gray-600 w-20 text-right">
					{minScorePct}% · {filtered.length}/{candidates.length}
				</span>
			</div>

			{filtered.length === 0 ? (
				<p className="text-gray-500 text-sm">
					No candidates match the current filter.
				</p>
			) : (
				<div className="space-y-3">
					{filtered.map((candidate) => (
						<CandidateCard
							key={candidate.id}
							candidate={candidate}
							seedText={seedText}
						/>
					))}
				</div>
			)}
		</div>
	);
}
