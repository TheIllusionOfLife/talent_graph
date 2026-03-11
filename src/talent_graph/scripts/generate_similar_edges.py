"""Generate SIMILAR_TO edges between persons based on embedding cosine similarity.

Usage:
    uv run python -m talent_graph.scripts.generate_similar_edges [--threshold 0.7] [--top-k 5]
"""

from __future__ import annotations

import argparse
import asyncio

import numpy as np
import structlog
from sqlalchemy import select

from talent_graph.graph.neo4j_client import run_write_query
from talent_graph.graph.queries import MERGE_SIMILAR_TO_BATCH
from talent_graph.storage.models import Person
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()

_MAX_PERSONS = 10_000


def _compute_similar_pairs(
    person_ids: list[str],
    embeddings: np.ndarray,
    threshold: float = 0.7,
    top_k: int = 5,
) -> list[dict[str, object]]:
    """Compute pairwise cosine similarity and return top-K pairs above threshold.

    Returns list of {"person_id_a": str, "person_id_b": str, "similarity": float}
    with canonical ordering (person_id_a < person_id_b).
    """
    n = len(person_ids)
    if n < 2:
        return []

    # Normalize for cosine similarity via dot product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    normed = embeddings / norms
    sim_matrix = normed @ normed.T

    # Collect top-K per person (above threshold), then deduplicate
    seen: set[tuple[str, str]] = set()
    pairs: list[dict[str, object]] = []

    for i in range(n):
        # Zero out self
        row = sim_matrix[i].copy()
        row[i] = -1.0

        # Get top-K indices above threshold
        above = np.where(row >= threshold)[0]
        if len(above) == 0:
            continue
        top_indices = above[np.argsort(row[above])[::-1]][:top_k]

        for j in top_indices:
            a, b = sorted([person_ids[i], person_ids[int(j)]])
            key = (a, b)
            if key not in seen:
                seen.add(key)
                pairs.append({
                    "person_id_a": a,
                    "person_id_b": b,
                    "similarity": round(float(row[int(j)]), 4),
                })

    return pairs


async def _load_embeddings() -> tuple[list[str], np.ndarray]:
    """Load all person embeddings from Postgres."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Person.id, Person.embedding).where(Person.embedding.isnot(None))
        )
        rows = result.all()

    if not rows:
        return [], np.array([])

    person_ids = [r[0] for r in rows]
    vecs = np.array([list(r[1]) for r in rows], dtype=np.float32)
    return person_ids, vecs


async def run(threshold: float = 0.7, top_k: int = 5) -> int:
    """Full pipeline: load embeddings → compute pairs → MERGE into Neo4j."""
    person_ids, vecs = await _load_embeddings()
    n = len(person_ids)

    if n == 0:
        log.info("similar_edges.skip", reason="no embeddings found")
        return 0

    if n > _MAX_PERSONS:
        log.warning(
            "similar_edges.skip",
            reason=f"N={n} exceeds {_MAX_PERSONS} — O(N^2) pairwise is impractical",
        )
        return 0

    log.info("similar_edges.computing", persons=n, threshold=threshold, top_k=top_k)
    pairs = _compute_similar_pairs(person_ids, vecs, threshold=threshold, top_k=top_k)

    if not pairs:
        log.info("similar_edges.skip", reason="no pairs above threshold")
        return 0

    # Batch MERGE into Neo4j
    batch_size = 500
    for i in range(0, len(pairs), batch_size):
        batch = pairs[i : i + batch_size]
        await run_write_query(MERGE_SIMILAR_TO_BATCH, {"pairs": batch})

    log.info("similar_edges.done", edges=len(pairs))
    return len(pairs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SIMILAR_TO edges from embeddings")
    parser.add_argument("--threshold", type=float, default=0.7, help="Minimum cosine similarity")
    parser.add_argument("--top-k", type=int, default=5, help="Max similar persons per person")
    args = parser.parse_args()
    asyncio.run(run(threshold=args.threshold, top_k=args.top_k))


if __name__ == "__main__":
    main()
