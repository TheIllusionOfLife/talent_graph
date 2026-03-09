"""Entity resolver orchestrator — deterministic first, heuristic fallback.

Pipeline:
  1. Deterministic (ORCID, github_login, homepage, email) → confidence 1.0
  2. Heuristic (name + org + concept similarity) → confidence 0.5–1.0
  3. New ULID if no match found

Side-effects:
  - person.canonical_person_id is set in-place.
  - Heuristic candidates (0.5 ≤ conf < 0.8) are written to entity_links.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from talent_graph.entity_resolution.deterministic import resolve_deterministic
from talent_graph.entity_resolution.heuristic import (
    compute_heuristic_confidence,
    is_auto_merge,
    is_queue_candidate,
)
from talent_graph.normalize.common_schema import PersonRecord
from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import EntityLink, Person

log = structlog.get_logger()

# Max number of existing persons to compare heuristically (prevents O(N^2) at scale).
_HEURISTIC_CANDIDATE_LIMIT = 500


async def _write_entity_link(
    session: AsyncSession,
    person_id_a: str,
    person_id_b: str,
    confidence: float,
    method: str = "heuristic",
) -> None:
    """Insert an entity_links row (canonical ordering: id_a < id_b)."""
    id_a, id_b = sorted([person_id_a, person_id_b])
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    stmt = (
        pg_insert(EntityLink)
        .values(
            id=new_id(),
            person_id_a=id_a,
            person_id_b=id_b,
            confidence=confidence,
            method=method,
            status="pending",
        )
        .on_conflict_do_nothing(index_elements=["person_id_a", "person_id_b"])
    )
    await session.execute(stmt)


async def _resolve_heuristic(
    session: AsyncSession,
    person: PersonRecord,
) -> str | None:
    """Return canonical_person_id of best heuristic match, or None.

    Writes queue candidates to entity_links.
    Requires person.canonical_person_id to be set (used as person_id_a for entity_links).
    """
    # Fetch candidate persons — limit to keep latency bounded
    result = await session.execute(
        select(Person.id, Person.name, Person.org_id).limit(_HEURISTIC_CANDIDATE_LIMIT)
    )
    rows = result.all()

    best_id: str | None = None
    best_conf: float = 0.0

    for row in rows:
        candidate = PersonRecord(name=row.name)
        conf = compute_heuristic_confidence(person, candidate, concepts_a=[], concepts_b=[])

        if conf > best_conf:
            best_conf = conf
            best_id = row.id

    if best_id and is_auto_merge(best_conf):
        log.info(
            "er.heuristic.auto_merge",
            name=person.name,
            matched_id=best_id,
            confidence=best_conf,
        )
        return best_id

    if best_id and is_queue_candidate(best_conf) and person.canonical_person_id:
        log.info(
            "er.heuristic.queued",
            name=person.name,
            candidate_id=best_id,
            confidence=best_conf,
        )
        await _write_entity_link(session, person.canonical_person_id, best_id, best_conf)

    return None


async def resolve_person(session: AsyncSession, person: PersonRecord) -> str:
    """Resolve a PersonRecord to a canonical_person_id (assigned in-place).

    Returns the canonical_person_id (new or existing).
    """
    # 1. Deterministic
    canon_id = await resolve_deterministic(session, person)
    if canon_id:
        person.canonical_person_id = canon_id
        log.debug("er.deterministic.match", name=person.name, canon_id=canon_id)
        return canon_id

    # 2. Assign a tentative new ID so heuristic can write entity_links
    tentative_id = new_id()
    person.canonical_person_id = tentative_id

    # 3. Heuristic
    heuristic_id = await _resolve_heuristic(session, person)
    if heuristic_id:
        person.canonical_person_id = heuristic_id
        return heuristic_id

    # 4. New person — keep tentative ULID
    log.debug("er.new_person", name=person.name, canon_id=tentative_id)
    return tentative_id
