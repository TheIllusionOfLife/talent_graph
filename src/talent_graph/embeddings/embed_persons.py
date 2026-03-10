"""Batch-generate and store embeddings for all persons in Postgres.

Run after ingestion to ensure every Person row has an embedding before search
and discovery queries are called. Idempotent: skips persons with existing embeddings
unless force=True.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from talent_graph.embeddings.generator import encode
from talent_graph.embeddings.text_builder import build_person_text
from talent_graph.storage.models import Person
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.vector_store import upsert_embedding

log = structlog.get_logger()

_BATCH_SIZE = 32


async def embed_all_persons(force: bool = False) -> int:
    """Generate and store embeddings for all persons.

    Fetches person IDs first (lightweight), then loads each batch with eager
    relations (org, papers) to avoid holding all rows in memory at once.

    Args:
        force: If True, re-embed persons that already have embeddings.

    Returns:
        Number of persons embedded.
    """
    # Phase 1: collect IDs only — avoids loading all related data into memory
    async with get_db_session() as session:
        id_stmt = select(Person.id)
        if not force:
            id_stmt = id_stmt.where(Person.embedding.is_(None))
        result = await session.execute(id_stmt)
        person_ids: list[str] = list(result.scalars().all())

    if not person_ids:
        log.info("embeddings.embed_all.skip", reason="no persons need embedding")
        return 0

    log.info("embeddings.embed_all.start", count=len(person_ids))

    # Phase 2: process one batch at a time — load full data only for the current batch
    embedded = 0
    for i in range(0, len(person_ids), _BATCH_SIZE):
        batch_ids = person_ids[i : i + _BATCH_SIZE]

        async with get_db_session() as session:
            batch_result = await session.execute(
                select(Person)
                .options(selectinload(Person.org), selectinload(Person.papers))
                .where(Person.id.in_(batch_ids))
            )
            batch = batch_result.scalars().all()

        texts = [
            build_person_text(
                name=p.name,
                org_name=p.org.name if p.org else None,
                paper_titles=[paper.title for paper in p.papers],
            )
            for p in batch
        ]

        vecs = encode(texts)

        async with get_db_session() as session:
            for person, vec in zip(batch, vecs, strict=True):
                await upsert_embedding(session, person.id, vec)

        embedded += len(batch)
        log.info("embeddings.embed_all.progress", embedded=embedded, total=len(person_ids))

    log.info("embeddings.embed_all.done", embedded=embedded)
    return embedded
