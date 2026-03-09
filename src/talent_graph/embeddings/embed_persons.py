"""Batch-generate and store embeddings for all persons in Postgres.

Run after ingestion to ensure every Person row has an embedding before search
and discovery queries are called. Idempotent: skips persons with existing embeddings
unless force=True.
"""

import structlog
from sqlalchemy import select

from talent_graph.embeddings.generator import encode
from talent_graph.embeddings.text_builder import build_person_text
from talent_graph.storage.models import Person
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.vector_store import upsert_embedding

log = structlog.get_logger()

_BATCH_SIZE = 32


async def embed_all_persons(force: bool = False) -> int:
    """Generate and store embeddings for all persons.

    Args:
        force: If True, re-embed persons that already have embeddings.

    Returns:
        Number of persons embedded.
    """
    async with get_db_session() as session:
        stmt = select(Person).options()
        if not force:
            stmt = stmt.where(Person.embedding.is_(None))
        result = await session.execute(stmt)
        persons = result.scalars().all()

    if not persons:
        log.info("embeddings.embed_all.skip", reason="no persons need embedding")
        return 0

    log.info("embeddings.embed_all.start", count=len(persons))

    embedded = 0
    for i in range(0, len(persons), _BATCH_SIZE):
        batch = persons[i : i + _BATCH_SIZE]

        # Build text representations
        texts = [
            build_person_text(
                name=p.name,
                # org and papers not eagerly loaded here; use name only for batch efficiency
            )
            for p in batch
        ]

        # Encode batch
        vecs = encode(texts)

        # Store each embedding
        async with get_db_session() as session:
            for person, vec in zip(batch, vecs, strict=True):
                await upsert_embedding(session, person.id, vec)

        embedded += len(batch)
        log.info("embeddings.embed_all.progress", embedded=embedded, total=len(persons))

    log.info("embeddings.embed_all.done", embedded=embedded)
    return embedded
