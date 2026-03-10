"""GET /person/{id} — return person detail with papers, repos, and org."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from talent_graph.api.deps import require_api_key
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
