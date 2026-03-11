"use client";

import Link from "next/link";
import { useState } from "react";
import { AddToShortlistButton } from "@/components/AddToShortlistButton";
import { getPersonBrief } from "@/lib/api";
import type { CandidateResult } from "@/types";

interface CandidateCardProps {
	candidate: CandidateResult;
	seedText?: string;
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

export function CandidateCard({ candidate, seedText }: CandidateCardProps) {
	const [explaining, setExplaining] = useState(false);
	const [explainResult, setExplainResult] = useState<string | null>(null);
	const [explainError, setExplainError] = useState<string | null>(null);

	async function handleExplain() {
		if (!seedText) return;
		setExplaining(true);
		setExplainError(null);
		try {
			const brief = await getPersonBrief(candidate.id, seedText);
			setExplainResult(brief.explanation);
		} catch (e) {
			setExplainError(e instanceof Error ? e.message : "Failed");
		} finally {
			setExplaining(false);
		}
	}

	const personHref = seedText
		? `/person/${candidate.id}?q=${encodeURIComponent(seedText)}`
		: `/person/${candidate.id}`;

	return (
		<div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
			<div className="flex items-start justify-between mb-3">
				<div>
					<Link
						href={personHref}
						className="text-blue-700 font-semibold hover:underline"
					>
						{candidate.name}
					</Link>
					<p className="text-xs text-gray-400 mt-0.5">
						{candidate.hop_distance}-hop · Score: {candidate.score.toFixed(3)}
					</p>
				</div>
				<div className="flex items-center gap-2">
					<span className="text-lg font-bold text-blue-700">
						{Math.round(candidate.score * 100)}
					</span>
					<AddToShortlistButton personId={candidate.id} />
				</div>
			</div>

			{candidate.explanation && (
				<p className="text-xs text-gray-600 italic mb-3 border-l-2 border-blue-200 pl-2">
					{candidate.explanation}
				</p>
			)}

			{!candidate.explanation && !explainResult && seedText && (
				<button
					type="button"
					onClick={handleExplain}
					disabled={explaining}
					className="text-xs text-blue-500 hover:underline disabled:text-gray-400 mb-3"
				>
					{explaining ? "Explaining…" : "Explain"}
				</button>
			)}
			{explainResult && (
				<p className="text-xs text-gray-600 italic mb-3 border-l-2 border-blue-200 pl-2">
					{explainResult}
				</p>
			)}
			{explainError && (
				<p className="text-xs text-red-400 mb-2">{explainError}</p>
			)}

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
