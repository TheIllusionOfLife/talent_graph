"""GET /discovery/{entity_type}/{entity_id} — graph-based candidate ranking."""

import asyncio
from datetime import datetime
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from talent_graph.api.deps import require_user_key
from talent_graph.api.limiter import limiter
from talent_graph.embeddings.generator import encode_one_async
from talent_graph.embeddings.text_builder import build_person_text, build_query_text
from talent_graph.explain.explanation_engine import explain as generate_explanation
from talent_graph.features.person_features import (
    PersonFeatures,
    compute_credibility,
    compute_evidence_quality,
    compute_growth,
    compute_novelty,
)
from talent_graph.graph.neo4j_client import run_query
from talent_graph.ranking.modes import RankMode
from talent_graph.ranking.scorer import score_candidate
from talent_graph.storage.models import Concept, Paper, Person
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()
router = APIRouter(prefix="/discovery", tags=["discovery"])

_RECENT_YEARS = 2


def _current_year() -> int:
    return datetime.now().year


# ── Cypher queries ──────────────────────────────────────────────────────────

_CANDIDATES_FROM_PAPER = """
MATCH (seed:Paper {openalex_work_id: $seed_id})
MATCH path = shortestPath((seed)-[*1..3]-(candidate:Person))
RETURN candidate.person_id AS person_id, length(path) AS hops
ORDER BY hops
LIMIT $limit
"""

_CANDIDATES_FROM_PERSON = """
MATCH (seed:Person {person_id: $seed_id})
MATCH path = shortestPath((seed)-[*1..3]-(candidate:Person))
WHERE candidate.person_id <> $seed_id
RETURN candidate.person_id AS person_id, length(path) AS hops
ORDER BY hops
LIMIT $limit
"""

_CANDIDATES_FROM_CONCEPT = """
MATCH (seed:Concept {openalex_concept_id: $seed_id})
MATCH path = shortestPath((seed)-[*1..3]-(candidate:Person))
RETURN candidate.person_id AS person_id, length(path) AS hops
ORDER BY hops
LIMIT $limit
"""

_QUERY_MAP = {
    "paper": _CANDIDATES_FROM_PAPER,
    "person": _CANDIDATES_FROM_PERSON,
    "concept": _CANDIDATES_FROM_CONCEPT,
}


# ── Response models ─────────────────────────────────────────────────────────


class ScoreBreakdown(BaseModel):
    semantic_similarity: float
    graph_proximity: float
    novelty: float
    growth: float
    evidence_quality: float
    credibility: float


class CandidateResult(BaseModel):
    id: str
    name: str
    score: float
    breakdown: ScoreBreakdown
    hop_distance: int
    explanation: str | None = None


class DiscoveryResponse(BaseModel):
    seed_entity_type: str
    seed_entity_id: str
    mode: str
    candidates: list[CandidateResult]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _graph_proximity(hops: int) -> float:
    """Convert hop distance to [0, 1] score. Fewer hops = higher proximity."""
    if hops <= 0:
        return 1.0
    return 1.0 / hops


def _recent_papers(papers: list) -> int:
    cutoff = _current_year() - _RECENT_YEARS
    return sum(1 for p in papers if p.publication_year and p.publication_year >= cutoff)


async def _resolve_seed(entity_type: str, entity_id: str) -> tuple[str | None, str]:
    """Single DB round-trip: return (neo4j_key, embedding_text) for the seed entity."""
    async with get_db_session() as session:
        if entity_type == "paper":
            row = await session.get(Paper, entity_id)
            if row is None:
                return None, ""
            text = build_query_text(f"{row.title} {' '.join(row.concepts or [])}")
            return row.openalex_work_id, text

        if entity_type == "person":
            person_result = await session.execute(
                select(Person)
                .options(selectinload(Person.papers), selectinload(Person.org))
                .where(Person.id == entity_id)
            )
            person_row = person_result.scalar_one_or_none()
            if person_row is None:
                return None, ""
            text = build_person_text(
                name=person_row.name,
                org_name=person_row.org.name if person_row.org else None,
                paper_titles=[p.title for p in person_row.papers],
            )
            return person_row.id, text

        if entity_type == "concept":
            concept_row = await session.get(Concept, entity_id)
            if concept_row is None:
                return None, ""
            return concept_row.openalex_concept_id, build_query_text(concept_row.name)

    return None, ""


# ── Route ───────────────────────────────────────────────────────────────────


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=DiscoveryResponse,
    dependencies=[Depends(require_user_key)],
)
@limiter.limit("20/minute")
async def discover_candidates(
    request: Request,
    entity_type: Literal["paper", "person", "concept"],
    entity_id: str,
    mode: RankMode = Query(default=RankMode.STANDARD),
    limit: int = Query(default=20, ge=1, le=100),
    explain: bool = Query(default=False),
) -> DiscoveryResponse:
    """Find and rank candidate persons related to a seed entity."""
    # 1. Resolve seed (single DB round-trip)
    neo4j_seed_id, seed_text = await _resolve_seed(entity_type, entity_id)

    if neo4j_seed_id is None:
        raise HTTPException(status_code=404, detail="Seed entity not found")

    # 2. Embed seed text (offloaded to thread pool — inference is CPU-bound)
    query_vec = await encode_one_async(seed_text) if seed_text else [0.0] * 384

    # 3. Get candidate person_ids from Neo4j graph traversal
    try:
        graph_rows = await run_query(
            _QUERY_MAP[entity_type],
            {"seed_id": neo4j_seed_id, "limit": limit * 3},
        )
    except Exception as exc:
        log.warning("discovery.neo4j.failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Graph database unavailable") from exc

    if not graph_rows:
        return DiscoveryResponse(
            seed_entity_type=entity_type,
            seed_entity_id=entity_id,
            mode=mode.value,
            candidates=[],
        )

    # Build hop map {person_id: min_hops}
    hop_map: dict[str, int] = {}
    for row in graph_rows:
        pid = row["person_id"]
        hops = int(row["hops"])
        if pid not in hop_map or hops < hop_map[pid]:
            hop_map[pid] = hops

    # 4. Fetch person data from Postgres
    person_ids = list(hop_map.keys())
    async with get_db_session() as session:
        result = await session.execute(
            select(Person)
            .options(selectinload(Person.papers), selectinload(Person.org))
            .where(Person.id.in_(person_ids))
        )
        persons = result.scalars().all()

    # 5. Compute features and score each candidate
    candidates: list[CandidateResult] = []
    for person in persons:
        hops = hop_map.get(person.id, 3)
        papers = person.papers or []
        total_citations = sum(p.citation_count for p in papers)
        recent_count = _recent_papers(papers)
        # Use earliest publication year as career start to compute career length
        now = _current_year()
        first_year = min(
            (p.publication_year for p in papers if p.publication_year),
            default=now,
        )
        years_active = max(1, now - first_year + 1)

        # Semantic similarity: use candidate's stored embedding vs query_vec
        if person.embedding:
            dot = sum(a * b for a, b in zip(person.embedding, query_vec, strict=True))
            sem_sim = max(0.0, min(1.0, (dot + 1.0) / 2.0))
        else:
            sem_sim = 0.5  # neutral fallback

        source_count = sum(
            1 for v in [person.openalex_author_id, person.github_login, person.orcid] if v
        )

        features = PersonFeatures(
            semantic_similarity=sem_sim,
            graph_proximity=_graph_proximity(hops),
            novelty=compute_novelty(total_citations, len(papers)),
            growth=compute_growth(recent_count, len(papers), years_active),
            evidence_quality=compute_evidence_quality(source_count),
            credibility=compute_credibility(person.org.name if person.org else None),
        )

        final_score = score_candidate(features, mode)
        candidates.append(
            CandidateResult(
                id=person.id,
                name=person.name,
                score=round(final_score, 4),
                breakdown=ScoreBreakdown(
                    semantic_similarity=round(features.semantic_similarity, 4),
                    graph_proximity=round(features.graph_proximity, 4),
                    novelty=round(features.novelty, 4),
                    growth=round(features.growth, 4),
                    evidence_quality=round(features.evidence_quality, 4),
                    credibility=round(features.credibility, 4),
                ),
                hop_distance=hops,
            )
        )

    candidates.sort(key=lambda c: c.score, reverse=True)
    final_candidates = candidates[:limit]

    # Generate explanations for top-3 after ranking+slicing (does not affect scores)
    if explain and seed_text and final_candidates:
        # Build a person lookup for the top-3
        top3 = final_candidates[:3]
        person_map = {p.id: p for p in persons}

        async def _explain_candidate(candidate: CandidateResult) -> str | None:
            person = person_map.get(candidate.id)
            if person is None:
                return None
            breakdown = {
                "semantic_similarity": candidate.breakdown.semantic_similarity,
                "graph_proximity": candidate.breakdown.graph_proximity,
                "novelty": candidate.breakdown.novelty,
                "growth": candidate.breakdown.growth,
                "evidence_quality": candidate.breakdown.evidence_quality,
                "credibility": candidate.breakdown.credibility,
            }
            try:
                return await generate_explanation(
                    person, seed_text, breakdown, candidate.hop_distance
                )
            except Exception as exc:
                log.warning("discovery.explain.failed", person_id=candidate.id, error=str(exc))
                return None

        explanations = await asyncio.gather(*[_explain_candidate(c) for c in top3])
        for candidate, explanation in zip(top3, explanations, strict=True):
            candidate.explanation = explanation

    return DiscoveryResponse(
        seed_entity_type=entity_type,
        seed_entity_id=entity_id,
        mode=mode.value,
        candidates=final_candidates,
    )
