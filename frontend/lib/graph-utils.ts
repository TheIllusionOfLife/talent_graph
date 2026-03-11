import type { EgoGraphResponse } from "@/types";

export interface ForceNode {
	id: string;
	type: string;
	label: string;
	metadata: Record<string, unknown>;
	isCenter: boolean;
	x?: number;
	y?: number;
}

export interface ForceLink {
	source: string | ForceNode;
	target: string | ForceNode;
	type: string;
}

export function escapeHtml(str: string): string {
	return str
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}

export function mergeGraphData(
	existing: { nodes: ForceNode[]; links: ForceLink[] },
	incoming: EgoGraphResponse,
	centerId: string,
): { nodes: ForceNode[]; links: ForceLink[]; truncated: boolean } {
	const nodeMap = new Map(existing.nodes.map((n) => [n.id, n]));
	for (const n of incoming.nodes) {
		if (!nodeMap.has(n.id)) {
			nodeMap.set(n.id, {
				...n,
				isCenter: n.id === centerId,
			});
		}
	}
	// Recompute isCenter for all nodes (handles re-centering on existing node)
	for (const [id, node] of nodeMap) {
		node.isCenter = id === centerId;
	}

	const linkSet = new Set(
		existing.links.map((l) => {
			const src = typeof l.source === "string" ? l.source : l.source.id;
			const tgt = typeof l.target === "string" ? l.target : l.target.id;
			return `${src}|${tgt}|${l.type}`;
		}),
	);
	const mergedLinks = [...existing.links];
	for (const l of incoming.links) {
		const key = `${l.source}|${l.target}|${l.type}`;
		const reverseKey = `${l.target}|${l.source}|${l.type}`;
		if (!linkSet.has(key) && !linkSet.has(reverseKey)) {
			linkSet.add(key);
			mergedLinks.push({ source: l.source, target: l.target, type: l.type });
		}
	}

	return {
		nodes: Array.from(nodeMap.values()),
		links: mergedLinks,
		truncated: incoming.truncated,
	};
}
