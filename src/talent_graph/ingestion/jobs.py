"""Ingestion job orchestrators — fetch → normalize → resolve → persist."""

import hashlib
import json

import structlog

from talent_graph.config.settings import get_settings
from talent_graph.graph.graph_builder import GraphBuilder
from talent_graph.ingestion.openalex_client import OpenAlexClient
from talent_graph.normalize.normalize_openalex import normalize_work
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.raw_store import RawStore
from talent_graph.storage.upsert import upsert_concept, upsert_org, upsert_paper, upsert_person

log = structlog.get_logger()


def _work_id(raw_work: dict, fallback_index: int) -> str:
    """Extract stable work ID from raw response; use content-hash fallback."""
    raw_id = raw_work.get("id", "")
    if raw_id:
        return raw_id.split("/")[-1]
    # Fallback: hash of content (stable across re-runs; avoids "unknown" collision)
    content_hash = hashlib.sha1(
        json.dumps(raw_work, sort_keys=True).encode(), usedforsecurity=False
    ).hexdigest()[:12]
    return f"noid_{content_hash}"


async def ingest_openalex(
    query: str,
    max_results: int = 200,
    raw_store: RawStore | None = None,
    graph_builder: GraphBuilder | None = None,
) -> dict[str, int]:
    """
    Full OpenAlex ingestion pipeline:
      fetch → save raw → normalize → upsert postgres → upsert neo4j

    Returns counts of upserted entities (existing records count as 0 on re-run).
    """
    settings = get_settings()
    store = raw_store or RawStore()
    builder = graph_builder or GraphBuilder()

    counts = {"papers": 0, "persons": 0, "orgs": 0, "concepts": 0}

    async with OpenAlexClient(email=settings.openalex_email) as client:
        log.info("openalex.fetch.start", query=query, max_results=max_results)
        raw_works = await client.get_works_paginated(query=query, max_results=max_results)
        log.info("openalex.fetch.done", count=len(raw_works))

    for i, raw_work in enumerate(raw_works):
        work_id = _work_id(raw_work, i)

        # Save raw JSON before any processing (safe even on partial failure)
        store.save("openalex", "works", work_id, raw_work)

        # Normalize
        paper = normalize_work(raw_work)

        # Assign canonical IDs (stub: use openalex author ID as person_id for now;
        # Sprint 2 adds full entity resolution via deterministic + heuristic matching)
        for authorship in paper.authors:
            person = authorship.person
            if person.openalex_author_id and person.canonical_person_id is None:
                person.canonical_person_id = f"person_{person.openalex_author_id}"

        # Upsert to Postgres (single transaction per paper)
        async with get_db_session() as session:
            # Orgs (guarded: only when openalex_institution_id is present)
            orgs_seen: set[str] = set()
            for authorship in paper.authors:
                org = authorship.person.org
                if (
                    org
                    and org.openalex_institution_id
                    and org.openalex_institution_id not in orgs_seen
                ):
                    orgs_seen.add(org.openalex_institution_id)
                    await upsert_org(session, org)
                    counts["orgs"] += 1

            # Persons
            persons_seen: set[str] = set()
            for authorship in paper.authors:
                pid = authorship.person.canonical_person_id
                if pid and pid not in persons_seen:
                    persons_seen.add(pid)
                    await upsert_person(session, authorship.person)
                    counts["persons"] += 1

            # Concepts
            for concept in paper.concepts:
                await upsert_concept(session, concept)
                counts["concepts"] += 1

            # Paper + PaperAuthor join rows
            await upsert_paper(session, paper)
            counts["papers"] += 1

        # Upsert to Neo4j
        await builder.upsert_paper(paper)

    log.info("openalex.ingest.done", **counts)
    return counts
