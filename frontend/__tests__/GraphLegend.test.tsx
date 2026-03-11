import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GraphLegend } from "@/components/GraphLegend";

describe("GraphLegend", () => {
	it("renders all 5 legend items", () => {
		render(<GraphLegend />);
		for (const label of ["Person", "Paper", "Repo", "Concept", "Org"]) {
			expect(screen.getByText(label)).toBeInTheDocument();
		}
	});

	it("renders colored indicators with correct colors", () => {
		const { container } = render(<GraphLegend />);
		const dots = container.querySelectorAll("span.rounded-full");
		expect(dots).toHaveLength(5);

		// jsdom normalizes hex colors to rgb()
		const expected = [
			"rgb(59, 130, 246)",
			"rgb(34, 197, 94)",
			"rgb(249, 115, 22)",
			"rgb(168, 85, 247)",
			"rgb(107, 114, 128)",
		];
		for (const [i, dot] of Array.from(dots).entries()) {
			expect((dot as HTMLElement).style.backgroundColor).toBe(expected[i]);
		}
	});
});
