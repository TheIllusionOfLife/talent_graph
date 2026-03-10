"""Offline evaluation framework for search quality.

Usage:
    uv run python -m talent_graph.scripts.evaluate [--api-url URL] [--api-key KEY] [--top-k 10]

Loads curated query fixtures from tests/evaluation/fixtures/queries.json,
calls GET /search for each query, and computes precision@k and MRR.

Queries with empty expected_person_ids are skipped (not yet annotated).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

_FIXTURES_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "tests"
    / "evaluation"
    / "fixtures"
    / "queries.json"
)


def _precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for pid in top_k if pid in relevant)
    return hits / k if k > 0 else 0.0


def _reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for rank, pid in enumerate(retrieved, start=1):
        if pid in relevant:
            return 1.0 / rank
    return 0.0


def run_evaluation(api_url: str, api_key: str, top_k: int) -> None:
    fixtures_path = _FIXTURES_PATH
    if not fixtures_path.exists():
        print(f"Fixtures file not found: {fixtures_path}", file=sys.stderr)
        sys.exit(1)

    with fixtures_path.open() as f:
        queries: list[dict] = json.load(f)

    annotated = [q for q in queries if q.get("expected_person_ids")]
    skipped = len(queries) - len(annotated)

    if not annotated:
        print(
            "No annotated queries found. Populate 'expected_person_ids' in "
            "tests/evaluation/fixtures/queries.json after seeding data."
        )
        if skipped:
            print(f"({skipped} queries skipped — no expected IDs)")
        return

    headers = {"X-API-Key": api_key}
    precision_5_scores: list[float] = []
    precision_10_scores: list[float] = []
    mrr_scores: list[float] = []

    col_w = 50
    print(f"\n{'Query':<{col_w}} {'P@5':>6} {'P@10':>6} {'MRR':>6}")
    print("-" * (col_w + 22))

    with httpx.Client(base_url=api_url, headers=headers, timeout=30.0) as client:
        for item in annotated:
            query = item["query"]
            relevant = set(item["expected_person_ids"])

            try:
                resp = client.get("/search", params={"q": query, "limit": max(top_k, 10)})
                resp.raise_for_status()
                data = resp.json()
                retrieved = [r["id"] for r in data.get("results", [])]
            except Exception as exc:
                print(f"  ERROR for query '{query}': {exc}", file=sys.stderr)
                retrieved = []

            p5 = _precision_at_k(retrieved, relevant, 5)
            p10 = _precision_at_k(retrieved, relevant, 10)
            rr = _reciprocal_rank(retrieved, relevant)

            precision_5_scores.append(p5)
            precision_10_scores.append(p10)
            mrr_scores.append(rr)

            label = query[: col_w - 3] + "..." if len(query) > col_w else query
            print(f"{label:<{col_w}} {p5:>6.3f} {p10:>6.3f} {rr:>6.3f}")

    n = len(annotated)
    map5 = sum(precision_5_scores) / n
    map10 = sum(precision_10_scores) / n
    mean_mrr = sum(mrr_scores) / n

    print("-" * (col_w + 22))
    print(f"{'MEAN (n=' + str(n) + ')':<{col_w}} {map5:>6.3f} {map10:>6.3f} {mean_mrr:>6.3f}")
    if skipped:
        print(f"\n({skipped} queries skipped — no expected IDs annotated yet)")

    print(f"\nSummary: precision@5={map5:.3f}  precision@10={map10:.3f}  MRR={mean_mrr:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline evaluation for talent_graph search")
    parser.add_argument("--api-url", default="http://localhost:8000", help="FastAPI base URL")
    parser.add_argument("--api-key", default="change-me-in-production", help="API key")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results to retrieve")
    args = parser.parse_args()
    run_evaluation(api_url=args.api_url, api_key=args.api_key, top_k=args.top_k)


if __name__ == "__main__":
    main()
