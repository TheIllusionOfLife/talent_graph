"""pgvector operations for person embeddings."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from talent_graph.storage.models import Person


async def upsert_embedding(
    session: AsyncSession,
    person_id: str,
    vec: list[float],
) -> None:
    """Store or replace the embedding for a person.

    Raises ValueError if the person does not exist (data drift guard).
    """
    result = await session.execute(
        update(Person).where(Person.id == person_id).values(embedding=vec).returning(Person.id)
    )
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Person {person_id!r} not found — cannot store embedding")


async def search_similar(
    session: AsyncSession,
    query_vec: list[float],
    limit: int = 20,
) -> list[dict]:
    """Return top-K persons ordered by cosine distance to query_vec.

    Returns list of dicts with keys: id, name, distance (lower = more similar).
    """
    # pgvector <=> is cosine distance; 1 - cosine_similarity
    result = await session.execute(
        select(
            Person.id,
            Person.name,
            Person.embedding.cosine_distance(query_vec).label("distance"),
        )
        .where(Person.embedding.is_not(None))
        .order_by("distance")
        .limit(limit)
    )
    return [{"id": row.id, "name": row.name, "distance": row.distance} for row in result]
