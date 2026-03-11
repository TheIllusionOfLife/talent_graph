import { describe, expect, it } from "vitest";
import {
	escapeHtml,
	type ForceLink,
	type ForceNode,
	mergeGraphData,
} from "@/lib/graph-utils";
import type { EgoGraphResponse } from "@/types";

describe("escapeHtml", () => {
	it("escapes ampersands", () => {
		expect(escapeHtml("a & b")).toBe("a &amp; b");
	});

	it("escapes angle brackets", () => {
		expect(escapeHtml("<script>")).toBe("&lt;script&gt;");
	});

	it("escapes double quotes", () => {
		expect(escapeHtml('say "hi"')).toBe("say &quot;hi&quot;");
	});

	it("escapes single quotes", () => {
		expect(escapeHtml("it's")).toBe("it&#039;s");
	});

	it("escapes all entities together", () => {
		expect(escapeHtml(`<a href="x">&'`)).toBe(
			"&lt;a href=&quot;x&quot;&gt;&amp;&#039;",
		);
	});

	it("returns empty string unchanged", () => {
		expect(escapeHtml("")).toBe("");
	});
});

describe("mergeGraphData", () => {
	const makeNode = (id: string, type = "Person"): ForceNode => ({
		id,
		type,
		label: id,
		metadata: {},
		isCenter: false,
	});

	const makeLink = (
		source: string,
		target: string,
		type = "AUTHORED",
	): ForceLink => ({
		source,
		target,
		type,
	});

	const makeIncoming = (
		nodes: {
			id: string;
			type: string;
			label: string;
			metadata: Record<string, unknown>;
		}[],
		links: { source: string; target: string; type: string }[],
		truncated = false,
	): EgoGraphResponse => ({
		center_id: "A",
		nodes,
		links,
		truncated,
	});

	it("deduplicates nodes by id", () => {
		const existing = {
			nodes: [makeNode("A"), makeNode("B")],
			links: [],
		};
		const incoming = makeIncoming(
			[
				{ id: "B", type: "Person", label: "B", metadata: {} },
				{ id: "C", type: "Person", label: "C", metadata: {} },
			],
			[],
		);
		const result = mergeGraphData(existing, incoming, "A");
		expect(result.nodes).toHaveLength(3);
		const ids = result.nodes.map((n) => n.id).sort();
		expect(ids).toEqual(["A", "B", "C"]);
	});

	it("deduplicates links including reverse direction", () => {
		const existing = {
			nodes: [makeNode("A"), makeNode("B")],
			links: [makeLink("A", "B", "COAUTHORED_WITH")],
		};
		const incoming = makeIncoming(
			[{ id: "A", type: "Person", label: "A", metadata: {} }],
			[{ source: "B", target: "A", type: "COAUTHORED_WITH" }],
		);
		const result = mergeGraphData(existing, incoming, "A");
		expect(result.links).toHaveLength(1);
	});

	it("adds new links that are genuinely new", () => {
		const existing = {
			nodes: [makeNode("A"), makeNode("B")],
			links: [makeLink("A", "B")],
		};
		const incoming = makeIncoming(
			[{ id: "C", type: "Paper", label: "C", metadata: {} }],
			[{ source: "A", target: "C", type: "AUTHORED" }],
		);
		const result = mergeGraphData(existing, incoming, "A");
		expect(result.links).toHaveLength(2);
	});

	it("propagates truncated flag from incoming data", () => {
		const existing = { nodes: [makeNode("A")], links: [] };
		const incoming = makeIncoming([], [], true);
		const result = mergeGraphData(existing, incoming, "A");
		expect(result.truncated).toBe(true);
	});

	it("marks new center node correctly", () => {
		const existing = { nodes: [], links: [] };
		const incoming = makeIncoming(
			[{ id: "A", type: "Person", label: "A", metadata: {} }],
			[],
		);
		const result = mergeGraphData(existing, incoming, "A");
		expect(result.nodes[0].isCenter).toBe(true);
	});

	it("handles ForceNode objects in existing link source/target", () => {
		const nodeA = makeNode("A");
		const nodeB = makeNode("B");
		const existing = {
			nodes: [nodeA, nodeB],
			links: [{ source: nodeA, target: nodeB, type: "AUTHORED" } as ForceLink],
		};
		const incoming = makeIncoming(
			[],
			[{ source: "A", target: "B", type: "AUTHORED" }],
		);
		const result = mergeGraphData(existing, incoming, "A");
		expect(result.links).toHaveLength(1);
	});
});
