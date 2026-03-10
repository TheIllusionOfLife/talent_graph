"use client";

import { useEffect, useState } from "react";
import { getPersonBrief } from "@/lib/api";
import type { PersonBrief as PersonBriefType } from "@/types";

interface PersonBriefProps {
	personId: string;
	seedText: string;
}

export function PersonBrief({ personId, seedText }: PersonBriefProps) {
	const [brief, setBrief] = useState<PersonBriefType | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		setLoading(true);
		setError(null);
		getPersonBrief(personId, seedText)
			.then(setBrief)
			.catch((e: unknown) => {
				setError(e instanceof Error ? e.message : "Failed to load brief");
			})
			.finally(() => setLoading(false));
	}, [personId, seedText]);

	if (loading) {
		return (
			<div className="bg-white border border-gray-200 rounded-lg p-5 mb-4 animate-pulse">
				<div className="h-4 bg-gray-200 rounded w-1/4 mb-3" />
				<div className="h-3 bg-gray-100 rounded w-full mb-2" />
				<div className="h-3 bg-gray-100 rounded w-5/6 mb-2" />
				<div className="h-3 bg-gray-100 rounded w-3/4" />
			</div>
		);
	}

	if (error || !brief) {
		return null;
	}

	return (
		<div className="bg-blue-50 border border-blue-200 rounded-lg p-5 mb-4">
			<div className="flex items-center justify-between mb-2">
				<h2 className="text-sm font-semibold text-blue-800 uppercase tracking-wide">
					AI Brief
				</h2>
				{brief.fallback && (
					<span className="text-xs text-gray-400 italic">
						(template — MLX offline)
					</span>
				)}
			</div>

			<p className="text-gray-800 text-sm leading-relaxed mb-3">
				{brief.explanation}
			</p>

			{brief.evidence.length > 0 && (
				<div>
					<p className="text-xs font-medium text-blue-700 mb-1">Evidence</p>
					<ul className="space-y-1">
						{brief.evidence.map((e) => (
							<li
								key={`${e.type}-${e.label}`}
								className="flex items-start gap-2 text-xs text-gray-600"
							>
								<span className="mt-0.5 shrink-0">
									{e.type === "paper" ? "📄" : e.type === "repo" ? "💻" : "🏛"}
								</span>
								<span>
									{e.label}
									{e.detail && (
										<span className="text-gray-400 ml-1">· {e.detail}</span>
									)}
								</span>
							</li>
						))}
					</ul>
				</div>
			)}
		</div>
	);
}
