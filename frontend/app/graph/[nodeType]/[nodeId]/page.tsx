import Link from "next/link";
import { ForceGraph } from "@/components/ForceGraph";
import { fetchEgoGraph } from "@/lib/api";
import type { EgoGraphResponse } from "@/types";

interface GraphPageProps {
	params: Promise<{ nodeType: string; nodeId: string }>;
	searchParams: Promise<{ hops?: string }>;
}

export default async function GraphPage({
	params,
	searchParams,
}: GraphPageProps) {
	const { nodeType, nodeId } = await params;
	const { hops: hopsParam } = await searchParams;
	const hops = Math.min(3, Math.max(1, Number(hopsParam) || 2));

	let data: EgoGraphResponse | undefined;
	let error: string | null = null;

	try {
		data = await fetchEgoGraph(nodeType, nodeId, hops);
	} catch (e) {
		error = e instanceof Error ? e.message : "Failed to load graph";
	}

	if (error) {
		return (
			<main className="min-h-screen bg-gray-50 px-4 py-10">
				<div className="max-w-5xl mx-auto">
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
			<div className="max-w-5xl mx-auto">
				<div className="flex items-center gap-2 mb-6">
					<Link href="/" className="text-blue-600 hover:underline text-sm">
						← Search
					</Link>
					<span className="text-gray-400">/</span>
					{nodeType === "person" && (
						<Link
							href={`/person/${nodeId}`}
							className="text-blue-600 hover:underline text-sm"
						>
							Person Detail
						</Link>
					)}
					<span className="text-gray-400">/</span>
					<span className="text-sm text-gray-600">Graph</span>
				</div>

				<h1 className="text-2xl font-bold text-gray-900 mb-4">Network Graph</h1>
				<p className="text-sm text-gray-500 mb-6">
					Exploring {hops}-hop neighborhood · {data.nodes.length} nodes ·{" "}
					{data.links.length} connections
				</p>

				<ForceGraph initialData={data} />
			</div>
		</main>
	);
}
