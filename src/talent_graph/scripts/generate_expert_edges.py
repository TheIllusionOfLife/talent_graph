"""Generate LIKELY_EXPERT_IN edges based on paper-concept frequency.

A person gets a LIKELY_EXPERT_IN edge to a concept if they have authored
at least `min_papers` papers tagged with that concept.

Usage:
    uv run python -m talent_graph.scripts.generate_expert_edges [--min-papers 3]
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter

import structlog
from sqlalchemy import select

from talent_graph.graph.neo4j_client import run_write_query
from talent_graph.graph.queries import MERGE_LIKELY_EXPERT_IN_BATCH
from talent_graph.storage.models import Concept, Paper, PaperAuthor
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()


def _count_person_concepts(
    person_papers: list[dict[str, object]],
    min_papers: int = 3,
) -> list[dict[str, object]]:
    """Count papers per (person_id, concept_id) and return edges above threshold.

    Input: list of {"person_id": str, "concept_id": str}
    Output: list of {"person_id": str, "concept_id": str, "paper_count": int}
    """
    counter: Counter[tuple[str, str]] = Counter()
    for row in person_papers:
        key = (str(row["person_id"]), str(row["concept_id"]))
        counter[key] += 1

    return [
        {"person_id": pid, "concept_id": cid, "paper_count": count}
        for (pid, cid), count in counter.items()
        if count >= min_papers
    ]


async def _load_person_concept_pairs() -> list[dict[str, object]]:
    """Load all (person_id, concept_id) pairs from papers.

    Each paper has a concepts ARRAY column. For each paper an author wrote,
    we pair the author with each concept on that paper.
    """
    async with get_db_session() as session:
        # Get paper_id → person_id mapping
        pa_result = await session.execute(
            select(PaperAuthor.person_id, PaperAuthor.paper_id)
        )
        paper_authors = pa_result.all()

        if not paper_authors:
            return []

        # Get paper_id → concepts (openalex_concept_id) mapping
        paper_ids = list({pa.paper_id for pa in paper_authors})
        concept_result = await session.execute(
            select(Paper.id, Paper.concepts).where(Paper.id.in_(paper_ids))
        )
        paper_concepts_map: dict[str, list[str]] = {}
        for paper_id, concepts in concept_result:
            if concepts:
                paper_concepts_map[paper_id] = concepts

        # Also get concept openalex_id → concept.id mapping
        all_concept_names = set()
        for concepts in paper_concepts_map.values():
            all_concept_names.update(concepts)

        # Build (person_id, concept_name) pairs
        # Note: Paper.concepts stores concept names as strings (ARRAY(String))
        # We use the concept name directly as concept_id for the Cypher query
        # which matches on openalex_concept_id. Let's resolve via Concept table.
        concept_result2 = await session.execute(
            select(Concept.name, Concept.openalex_concept_id).where(
                Concept.name.in_(list(all_concept_names))
            )
        )
        name_to_id: dict[str, str] = {}
        for name, oa_id in concept_result2:
            if oa_id:
                name_to_id[name] = oa_id

    pairs: list[dict[str, object]] = []
    for pa in paper_authors:
        concepts = paper_concepts_map.get(pa.paper_id, [])
        for concept_name in concepts:
            concept_id = name_to_id.get(concept_name)
            if concept_id:
                pairs.append({"person_id": pa.person_id, "concept_id": concept_id})

    return pairs


async def run(min_papers: int = 3) -> int:
    """Full pipeline: load data → count → MERGE into Neo4j."""
    raw_pairs = await _load_person_concept_pairs()
    if not raw_pairs:
        log.info("expert_edges.skip", reason="no person-concept data")
        return 0

    log.info("expert_edges.computing", raw_pairs=len(raw_pairs), min_papers=min_papers)
    edges = _count_person_concepts(raw_pairs, min_papers=min_papers)

    if not edges:
        log.info("expert_edges.skip", reason="no edges above threshold")
        return 0

    # Batch MERGE into Neo4j
    batch_size = 500
    for i in range(0, len(edges), batch_size):
        batch = edges[i : i + batch_size]
        await run_write_query(MERGE_LIKELY_EXPERT_IN_BATCH, {"edges": batch})

    log.info("expert_edges.done", edges=len(edges))
    return len(edges)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LIKELY_EXPERT_IN edges")
    parser.add_argument("--min-papers", type=int, default=3, help="Min papers per concept")
    args = parser.parse_args()
    asyncio.run(run(min_papers=args.min_papers))


if __name__ == "__main__":
    main()
