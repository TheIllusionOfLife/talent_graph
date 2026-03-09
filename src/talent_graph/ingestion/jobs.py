"""Ingestion job orchestrators — fetch → normalize → resolve → persist."""

import structlog

from talent_graph.config.settings import get_settings
from talent_graph.graph.graph_builder import GraphBuilder
from talent_graph.ingestion.openalex_client import OpenAlexClient
from talent_graph.normalize.normalize_openalex import normalize_work
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.raw_store import RawStore
from talent_graph.storage.upsert import upsert_concept, upsert_org, upsert_paper, upsert_person

log = structlog.get_logger()


async def ingest_openalex(
    query: str,
    max_results: int = 200,
    raw_store: RawStore | None = None,
    graph_builder: GraphBuilder | None = None,
) -> dict[str, int]:
    """
    Full OpenAlex ingestion pipeline:
      fetch → save raw → normalize → upsert postgres → upsert neo4j

    Returns counts of ingested entities.
    """
    settings = get_settings()
    store = raw_store or RawStore()
    builder = graph_builder or GraphBuilder()

    counts = {"papers": 0, "persons": 0, "orgs": 0, "concepts": 0}

    async with OpenAlexClient(email=settings.openalex_email) as client:
        log.info("openalex.fetch.start", query=query, max_results=max_results)
        raw_works = await client.get_works_paginated(query=query, max_results=max_results)
        log.info("openalex.fetch.done", count=len(raw_works))

    for raw_work in raw_works:
        work_id = raw_work.get("id", "unknown").split("/")[-1]

        # Save raw JSON before any processing
        store.save("openalex", "works", work_id, raw_work)

        # Normalize
        paper = normalize_work(raw_work)

        # Assign canonical IDs (stub: use openalex ID as person_id for now;
        # Sprint 2 adds full entity resolution)
        for authorship in paper.authors:
            person = authorship.person
            if person.openalex_author_id and person.canonical_person_id is None:
                person.canonical_person_id = f"person_{person.openalex_author_id}"

        # Upsert to Postgres
        async with get_db_session() as session:
            # Orgs
            for authorship in paper.authors:
                if authorship.person.org and authorship.person.org.openalex_institution_id:
                    await upsert_org(session, authorship.person.org)
                    counts["orgs"] += 1

            # Persons
            for authorship in paper.authors:
                if authorship.person.canonical_person_id:
                    await upsert_person(session, authorship.person)
                    counts["persons"] += 1

            # Concepts
            for concept in paper.concepts:
                await upsert_concept(session, concept)
                counts["concepts"] += 1

            # Paper
            await upsert_paper(session, paper)
            counts["papers"] += 1

        # Upsert to Neo4j
        await builder.upsert_paper(paper)

    log.info("openalex.ingest.done", **counts)
    return counts
