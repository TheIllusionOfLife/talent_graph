"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchEgoGraph } from "@/lib/api";
import type { EgoGraphResponse } from "@/types";
import { GraphLegend } from "./GraphLegend";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
	ssr: false,
});
const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
	ssr: false,
});

function escapeHtml(str: string): string {
	return str
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}

const NODE_COLORS: Record<string, string> = {
	Person: "#3b82f6",
	Paper: "#22c55e",
	Repo: "#f97316",
	Concept: "#a855f7",
	Org: "#6b7280",
};

interface ForceNode {
	id: string;
	type: string;
	label: string;
	metadata: Record<string, unknown>;
	isCenter: boolean;
	x?: number;
	y?: number;
}

interface ForceLink {
	source: string | ForceNode;
	target: string | ForceNode;
	type: string;
}

interface ForceGraphProps {
	initialData: EgoGraphResponse;
}

function mergeGraphData(
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

export function ForceGraph({ initialData }: ForceGraphProps) {
	const router = useRouter();
	const [mode, setMode] = useState<"2d" | "3d">("2d");
	const [webglSupported, setWebglSupported] = useState(true);
	const [truncated, setTruncated] = useState(initialData.truncated);
	const [loading, setLoading] = useState(false);
	const expandedIds = useRef(new Set<string>());
	const clickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
	const lastClickedNodeId = useRef<string | null>(null);

	const initialForceData = useMemo(() => {
		const nodes: ForceNode[] = initialData.nodes.map((n) => ({
			...n,
			isCenter: n.id === initialData.center_id,
		}));
		const links: ForceLink[] = initialData.links.map((l) => ({
			source: l.source,
			target: l.target,
			type: l.type,
		}));
		return { nodes, links };
	}, [initialData]);

	const [graphData, setGraphData] = useState(initialForceData);

	useEffect(() => {
		try {
			const canvas = document.createElement("canvas");
			const gl =
				canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
			if (!gl) setWebglSupported(false);
		} catch {
			setWebglSupported(false);
		}
	}, []);

	const handleNodeClick = useCallback(
		(node: ForceNode) => {
			if (clickTimer.current && lastClickedNodeId.current === node.id) {
				clearTimeout(clickTimer.current);
				clickTimer.current = null;
				lastClickedNodeId.current = null;
				// Double-click same node: navigate to detail page
				const [nodeType, ...keyParts] = node.id.split("__");
				const nodeId = keyParts.join("__");
				if (nodeType === "person") {
					router.push(`/person/${nodeId}`);
				}
				return;
			}

			// Clear any pending timer from a different node
			if (clickTimer.current) {
				clearTimeout(clickTimer.current);
			}

			lastClickedNodeId.current = node.id;
			clickTimer.current = setTimeout(async () => {
				clickTimer.current = null;
				lastClickedNodeId.current = null;
				// Single-click: expand 1-hop subgraph
				if (expandedIds.current.has(node.id) || loading) return;

				const [nodeType, ...keyParts] = node.id.split("__");
				const nodeId = keyParts.join("__");

				// Only expand person nodes (others need lookup not yet implemented)
				if (nodeType !== "person") return;

				expandedIds.current.add(node.id);
				setLoading(true);
				try {
					const subgraph = await fetchEgoGraph(nodeType, nodeId, 1);
					setGraphData((prev) => {
						const merged = mergeGraphData(
							prev,
							subgraph,
							initialData.center_id,
						);
						setTruncated((prev) => prev || merged.truncated);
						return { nodes: merged.nodes, links: merged.links };
					});
				} catch {
					expandedIds.current.delete(node.id);
				} finally {
					setLoading(false);
				}
			}, 250);
		},
		[loading, router, initialData.center_id],
	);

	const handleReset = useCallback(() => {
		if (clickTimer.current) {
			clearTimeout(clickTimer.current);
			clickTimer.current = null;
		}
		lastClickedNodeId.current = null;
		expandedIds.current.clear();
		setGraphData(initialForceData);
		setTruncated(initialData.truncated);
	}, [initialForceData, initialData.truncated]);

	const nodeCanvasObject = useCallback(
		(node: ForceNode, ctx: CanvasRenderingContext2D) => {
			const x = node.x ?? 0;
			const y = node.y ?? 0;
			const size = node.isCenter ? 8 : 5;
			const color = NODE_COLORS[node.type] ?? "#999";

			ctx.beginPath();
			ctx.arc(x, y, size, 0, 2 * Math.PI);
			ctx.fillStyle = color;
			ctx.fill();

			if (node.isCenter) {
				ctx.strokeStyle = "#1e3a5f";
				ctx.lineWidth = 2;
				ctx.stroke();
			}

			// Label
			ctx.font = `${node.isCenter ? "bold " : ""}3px sans-serif`;
			ctx.textAlign = "center";
			ctx.textBaseline = "top";
			ctx.fillStyle = "#374151";
			const label =
				node.label.length > 20 ? `${node.label.slice(0, 18)}…` : node.label;
			ctx.fillText(label, x, y + size + 2);
		},
		[],
	);

	const nodeLabel = useCallback((node: object) => {
		const n = node as ForceNode;
		const meta = n.metadata;
		const parts = [escapeHtml(n.label), `Type: ${escapeHtml(n.type)}`];
		if (meta.citation_count != null)
			parts.push(`Citations: ${meta.citation_count}`);
		if (meta.stars != null) parts.push(`Stars: ${meta.stars}`);
		if (meta.name && meta.name !== n.label)
			parts.push(`Name: ${escapeHtml(String(meta.name))}`);
		return parts.join("\n");
	}, []);

	const GraphComponent =
		mode === "3d" && webglSupported ? ForceGraph3D : ForceGraph2D;

	return (
		<div className="relative">
			{/* Controls */}
			<div className="flex items-center gap-3 mb-3">
				{webglSupported && (
					<button
						type="button"
						onClick={() => setMode(mode === "2d" ? "3d" : "2d")}
						className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm font-medium"
					>
						{mode === "2d" ? "Switch to 3D" : "Switch to 2D"}
					</button>
				)}
				<button
					type="button"
					onClick={handleReset}
					className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-sm font-medium"
				>
					Reset
				</button>
				{loading && <span className="text-sm text-gray-400">Expanding…</span>}
				<div className="ml-auto">
					<GraphLegend />
				</div>
			</div>

			{/* Truncation notice */}
			{truncated && (
				<div className="mb-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
					Graph truncated — click nodes to explore further
				</div>
			)}

			{/* Graph */}
			<div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
				{/* Force-graph generic node type doesn't include our custom fields,
				so we cast callback props to satisfy the library's type constraints */}
				<GraphComponent
					graphData={graphData}
					nodeId="id"
					nodeLabel={nodeLabel as never}
					onNodeClick={handleNodeClick as never}
					linkDirectionalArrowLength={3.5}
					linkDirectionalArrowRelPos={1}
					linkLabel="type"
					width={900}
					height={600}
					{...(mode === "2d"
						? { nodeCanvasObject: nodeCanvasObject as never }
						: {
								nodeColor: ((n: ForceNode) =>
									NODE_COLORS[n.type] ?? "#999") as never,
								nodeVal: ((n: ForceNode) => (n.isCenter ? 4 : 1)) as never,
							})}
				/>
			</div>

			<p className="text-xs text-gray-400 mt-2">
				Click a person node to expand their network. Double-click to navigate to
				their profile.
			</p>
		</div>
	);
}
