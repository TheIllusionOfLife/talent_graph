"""Entity resolver orchestrator — deterministic first, heuristic fallback.

Pipeline:
  1. Deterministic (openalex_author_id, ORCID, github_login, homepage, email) → confidence 1.0
  2. Heuristic (name + org + concept similarity) → confidence 0.5–1.0
  3. New ULID if no match found

Side-effects:
  - person.canonical_person_id is set in-place by resolve_person().
  - Heuristic entity_links are written by write_heuristic_links(), which MUST be called
    AFTER upsert_person() to satisfy the FK constraint on entity_links.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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

# Max existing persons to compare heuristically (prevents O(N^2) at scale).
_HEURISTIC_CANDIDATE_LIMIT = 500


async def _find_heuristic_match(
    session: AsyncSession,
    person: PersonRecord,
) -> tuple[str | None, float]:
    """Return (best_candidate_id, confidence) from heuristic comparison.

    Does NOT write to DB — call write_heuristic_links() after upsert.
    """
    result = await session.execute(select(Person.id, Person.name).limit(_HEURISTIC_CANDIDATE_LIMIT))
    rows = result.all()

    best_id: str | None = None
    best_conf: float = 0.0

    for row in rows:
        candidate = PersonRecord(name=row.name)
        conf = compute_heuristic_confidence(person, candidate, concepts_a=[], concepts_b=[])
        if conf > best_conf:
            best_conf = conf
            best_id = row.id

    return best_id, best_conf


async def resolve_person(session: AsyncSession, person: PersonRecord) -> str:
    """Resolve a PersonRecord to a canonical_person_id (assigned in-place).

    Does NOT write entity_links — call write_heuristic_links() AFTER upsert_person().
    Returns the canonical_person_id (new or existing).
    """
    # 1. Deterministic
    canon_id = await resolve_deterministic(session, person)
    if canon_id:
        person.canonical_person_id = canon_id
        log.debug("er.deterministic.match", name=person.name, canon_id=canon_id)
        return canon_id

    # 2. Heuristic
    best_id, best_conf = await _find_heuristic_match(session, person)

    if best_id and is_auto_merge(best_conf):
        person.canonical_person_id = best_id
        log.info(
            "er.heuristic.auto_merge", name=person.name, matched_id=best_id, confidence=best_conf
        )
        return best_id

    # 3. New ULID — heuristic queue link written post-upsert by write_heuristic_links()
    new_canon_id = new_id()
    person.canonical_person_id = new_canon_id
    log.debug("er.new_person", name=person.name, canon_id=new_canon_id)
    return new_canon_id


async def write_heuristic_links(
    session: AsyncSession,
    person: PersonRecord,
) -> None:
    """Write entity_links for heuristic queue candidates.

    MUST be called AFTER upsert_person() so both person IDs satisfy FK constraints.
    Only writes for queue-threshold candidates (0.5 ≤ conf < 0.8).
    """
    if not person.canonical_person_id:
        return

    best_id, best_conf = await _find_heuristic_match(session, person)

    if best_id and is_queue_candidate(best_conf) and best_id != person.canonical_person_id:
        id_a, id_b = sorted([person.canonical_person_id, best_id])
        stmt = (
            pg_insert(EntityLink)
            .values(
                id=new_id(),
                person_id_a=id_a,
                person_id_b=id_b,
                confidence=best_conf,
                method="heuristic",
                status="pending",
            )
            .on_conflict_do_nothing(index_elements=["person_id_a", "person_id_b"])
        )
        await session.execute(stmt)
        log.info(
            "er.heuristic.queued",
            name=person.name,
            candidate_id=best_id,
            confidence=best_conf,
        )
