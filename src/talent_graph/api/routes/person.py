"""GET /person/{id} and POST /person/{id}/brief routes."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from talent_graph.api.deps import require_api_key
from talent_graph.explain.explanation_engine import explain
from talent_graph.storage.models import Person, Repo, RepoContributor
from talent_graph.storage.postgres import get_db_session

router = APIRouter(prefix="/person", tags=["person"])


class OrgOut(BaseModel):
    id: str
    name: str
    country_code: str | None = None
    type: str | None = None


class PaperOut(BaseModel):
    id: str
    title: str
    publication_year: int | None = None
    citation_count: int
    concepts: list[str]


class RepoOut(BaseModel):
    id: str
    full_name: str
    description: str | None = None
    language: str | None = None
    stars: int
    topics: list[str]


class PersonDetail(BaseModel):
    id: str
    name: str
    openalex_author_id: str | None = None
    github_login: str | None = None
    orcid: str | None = None
    email: str | None = None
    homepage: str | None = None
    hidden_expert_score: float | None = None
    org: OrgOut | None = None
    papers: list[PaperOut]
    repos: list[RepoOut]


class BriefRequest(BaseModel):
    seed_text: str = Field(..., min_length=1, max_length=2048)


class EvidenceItem(BaseModel):
    type: Literal["paper", "repo", "org"]
    label: str
    detail: str | None = None


class PersonBrief(BaseModel):
    person_id: str
    explanation: str
    evidence: list[EvidenceItem]
    fallback: bool


@router.get("/{person_id}", response_model=PersonDetail, dependencies=[Depends(require_api_key)])
async def get_person(person_id: str) -> PersonDetail:
    """Return full person detail including papers, repos, and org."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Person)
            .options(selectinload(Person.papers), selectinload(Person.org))
            .where(Person.id == person_id)
        )
        person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    # Fetch repos contributed to
    async with get_db_session() as session:
        repo_result = await session.execute(
            select(Repo)
            .join(RepoContributor, RepoContributor.repo_id == Repo.id)
            .where(RepoContributor.person_id == person_id)
            .order_by(RepoContributor.contributions.desc(), Repo.stars.desc(), Repo.id)
            .limit(20)
        )
        repos = repo_result.scalars().all()

    return PersonDetail(
        id=person.id,
        name=person.name,
        openalex_author_id=person.openalex_author_id,
        github_login=person.github_login,
        orcid=person.orcid,
        email=person.email,
        homepage=person.homepage,
        hidden_expert_score=person.hidden_expert_score,
        org=OrgOut(
            id=person.org.id,
            name=person.org.name,
            country_code=person.org.country_code,
            type=person.org.type,
        )
        if person.org
        else None,
        papers=[
            PaperOut(
                id=p.id,
                title=p.title,
                publication_year=p.publication_year,
                citation_count=p.citation_count,
                concepts=p.concepts or [],
            )
            for p in person.papers
        ],
        repos=[
            RepoOut(
                id=r.id,
                full_name=r.full_name,
                description=r.description,
                language=r.language,
                stars=r.stars,
                topics=r.topics or [],
            )
            for r in repos
        ],
    )


@router.post(
    "/{person_id}/brief",
    response_model=PersonBrief,
    dependencies=[Depends(require_api_key)],
)
async def get_person_brief(person_id: str, body: BriefRequest) -> PersonBrief:
    """Generate an LLM explanation brief for a candidate person.

    Always returns 200 with a valid PersonBrief — falls back to template if MLX is down.
    """
    async with get_db_session() as session:
        result = await session.execute(
            select(Person)
            .options(selectinload(Person.papers), selectinload(Person.org))
            .where(Person.id == person_id)
        )
        person = result.scalar_one_or_none()

    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    # Build a neutral score breakdown from available signals (no ranking context here)
    papers = person.papers or []
    total_citations = sum(p.citation_count for p in papers)
    score_breakdown = {
        "semantic_similarity": 0.5,
        "graph_proximity": 0.5,
        "novelty": 1.0 if total_citations == 0 else min(1.0, 100.0 / max(total_citations, 1)),
        "growth": 0.5,
        "evidence_quality": min(1.0, len(papers) / 10.0),
        "credibility": 0.9 if person.org else 0.3,
    }

    # Detect whether fallback was used by comparing with template output
    from talent_graph.explain.prompt_templates import render_template_fallback

    template_text = render_template_fallback(person, score_breakdown, seed_text=body.seed_text)
    explanation = await explain(person, body.seed_text, score_breakdown)
    used_fallback = explanation == template_text

    # Build evidence list from papers and org
    evidence: list[EvidenceItem] = []
    if person.org:
        evidence.append(EvidenceItem(type="org", label=person.org.name))
    top_papers = sorted(papers, key=lambda p: p.citation_count, reverse=True)[:5]
    for p in top_papers:
        evidence.append(
            EvidenceItem(
                type="paper",
                label=p.title,
                detail=f"{p.publication_year}, {p.citation_count} citations"
                if p.publication_year
                else f"{p.citation_count} citations",
            )
        )

    return PersonBrief(
        person_id=person_id,
        explanation=explanation,
        evidence=evidence,
        fallback=used_fallback,
    )
