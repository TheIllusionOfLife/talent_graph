const LEGEND_ITEMS = [
	{ type: "Person", color: "#3b82f6" },
	{ type: "Paper", color: "#22c55e" },
	{ type: "Repo", color: "#f97316" },
	{ type: "Concept", color: "#a855f7" },
	{ type: "Org", color: "#6b7280" },
] as const;

export function GraphLegend() {
	return (
		<div className="flex flex-wrap gap-4 text-xs text-gray-600">
			{LEGEND_ITEMS.map((item) => (
				<span key={item.type} className="flex items-center gap-1.5">
					<span
						className="inline-block w-3 h-3 rounded-full"
						style={{ backgroundColor: item.color }}
					/>
					{item.type}
				</span>
			))}
		</div>
	);
}
