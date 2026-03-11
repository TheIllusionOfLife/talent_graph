import { NextResponse } from "next/server";
import { fetchEgoGraph } from "@/lib/api";

export async function GET(
	request: Request,
	{ params }: { params: Promise<{ nodeType: string; nodeId: string }> },
) {
	const { nodeType, nodeId } = await params;
	const { searchParams } = new URL(request.url);
	const hops = Number(searchParams.get("hops")) || 1;

	try {
		const data = await fetchEgoGraph(nodeType, nodeId, hops);
		return NextResponse.json(data);
	} catch (e) {
		const message = e instanceof Error ? e.message : "Failed to fetch graph";
		return NextResponse.json({ error: message }, { status: 502 });
	}
}
