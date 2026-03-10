"use client";

import { useState } from "react";
import Link from "next/link";
import { addToShortlist, listShortlists } from "@/lib/api";
import type { CandidateResult, ShortlistSummary } from "@/types";

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
	const [shortlists, setShortlists] = useState<ShortlistSummary[] | null>(null);
	const [showDropdown, setShowDropdown] = useState(false);
	const [adding, setAdding] = useState<string | null>(null);
	const [added, setAdded] = useState<string | null>(null);
	const [addError, setAddError] = useState<string | null>(null);

	async function handleOpenDropdown() {
		if (!shortlists) {
			const data = await listShortlists().catch(() => []);
			setShortlists(data);
		}
		setShowDropdown((v) => !v);
	}

	async function handleAdd(shortlistId: string) {
		setAdding(shortlistId);
		setAddError(null);
		try {
			await addToShortlist(shortlistId, candidate.id);
			setAdded(shortlistId);
		} catch (e: unknown) {
			setAddError(e instanceof Error ? e.message : "Failed");
		} finally {
			setAdding(null);
			setShowDropdown(false);
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
					<div className="relative">
						<button
							type="button"
							onClick={handleOpenDropdown}
							className="text-xs px-2 py-1 border border-gray-200 rounded hover:bg-gray-50 text-gray-600"
							title="Add to shortlist"
						>
							{added ? "✓" : "+ List"}
						</button>
						{showDropdown && (
							<div className="absolute right-0 top-7 z-10 bg-white border border-gray-200 rounded shadow-md min-w-40">
								{shortlists === null ? (
									<p className="text-xs text-gray-400 p-2">Loading…</p>
								) : shortlists.length === 0 ? (
									<p className="text-xs text-gray-400 p-2">
										No shortlists.{" "}
										<Link href="/shortlists" className="text-blue-500 underline">
											Create one
										</Link>
									</p>
								) : (
									shortlists.map((sl) => (
										<button
											key={sl.id}
											type="button"
											disabled={adding === sl.id}
											onClick={() => handleAdd(sl.id)}
											className="w-full text-left text-xs px-3 py-2 hover:bg-gray-50 text-gray-700 truncate"
										>
											{adding === sl.id ? "Adding…" : sl.name}
										</button>
									))
								)}
							</div>
						)}
					</div>
				</div>
			</div>

			{candidate.explanation && (
				<p className="text-xs text-gray-600 italic mb-3 border-l-2 border-blue-200 pl-2">
					{candidate.explanation}
				</p>
			)}

			{addError && (
				<p className="text-xs text-red-400 mb-2">{addError}</p>
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
