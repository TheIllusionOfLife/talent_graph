"""SQLAlchemy upsert helpers (ON CONFLICT DO UPDATE — idempotent)."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from talent_graph.normalize.common_schema import (
    ConceptRecord,
    OrgRecord,
    PaperRecord,
    PersonRecord,
    RepoRecord,
)
from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import (
    Concept,
    EntityLink,
    Org,
    Paper,
    PaperAuthor,
    Person,
    Repo,
    RepoContributor,
)


async def upsert_org(session: AsyncSession, org: OrgRecord) -> str:
    """Upsert org by openalex_institution_id. Returns the org's PK.

    Raises ValueError if openalex_institution_id is None — ON CONFLICT on NULL
    never fires in PostgreSQL, causing phantom duplicates on re-ingest.
    """
    if not org.openalex_institution_id:
        raise ValueError("openalex_institution_id is required for upsert_org")

    stmt = (
        insert(Org)
        .values(
            id=new_id(),
            name=org.name,
            openalex_institution_id=org.openalex_institution_id,
            country_code=org.country_code,
            type=org.type,
        )
        .on_conflict_do_update(
            index_elements=["openalex_institution_id"],
            set_={"name": org.name, "country_code": org.country_code, "type": org.type},
        )
        .returning(Org.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def upsert_person(session: AsyncSession, person: PersonRecord) -> str:
    """Upsert person using canonical_person_id as primary key."""
    if not person.canonical_person_id:
        raise ValueError("canonical_person_id must be set before upserting")

    org_id: str | None = None
    if person.org and person.org.openalex_institution_id:
        result = await session.execute(
            select(Org.id).where(Org.openalex_institution_id == person.org.openalex_institution_id)
        )
        org_id = result.scalar_one_or_none()

    stmt = (
        insert(Person)
        .values(
            id=person.canonical_person_id,
            name=person.name,
            openalex_author_id=person.openalex_author_id,
            github_login=person.github_login,
            orcid=person.orcid,
            email=person.email,
            homepage=person.homepage,
            org_id=org_id,
        )
        .on_conflict_do_update(
            index_elements=["id"],
            set_={
                "name": person.name,
                "openalex_author_id": person.openalex_author_id,
                "github_login": person.github_login,
                "orcid": person.orcid,
                "email": person.email,
                "homepage": person.homepage,
                "org_id": org_id,
                "updated_at": func.now(),
            },
        )
        .returning(Person.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def upsert_concept(session: AsyncSession, concept: ConceptRecord) -> str:
    """Upsert concept by openalex_concept_id.

    Raises ValueError if openalex_concept_id is None — see upsert_org for rationale.
    """
    if not concept.openalex_concept_id:
        raise ValueError("openalex_concept_id is required for upsert_concept")

    stmt = (
        insert(Concept)
        .values(
            id=new_id(),
            name=concept.name,
            openalex_concept_id=concept.openalex_concept_id,
            level=concept.level,
        )
        .on_conflict_do_update(
            index_elements=["openalex_concept_id"],
            set_={"name": concept.name, "level": concept.level},
        )
        .returning(Concept.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def upsert_paper(session: AsyncSession, paper: PaperRecord) -> str:
    """Upsert paper by openalex_work_id."""
    stmt = (
        insert(Paper)
        .values(
            id=new_id(),
            title=paper.title,
            openalex_work_id=paper.openalex_work_id,
            doi=paper.doi,
            publication_year=paper.publication_year,
            citation_count=paper.citation_count,
            abstract=paper.abstract,
            concepts=[c.openalex_concept_id for c in paper.concepts],
        )
        .on_conflict_do_update(
            index_elements=["openalex_work_id"],
            set_={
                "title": paper.title,
                "citation_count": paper.citation_count,
                "abstract": paper.abstract,
                "concepts": [c.openalex_concept_id for c in paper.concepts],
            },
        )
        .returning(Paper.id)
    )
    result = await session.execute(stmt)
    paper_db_id = result.scalar_one()

    # Upsert PaperAuthor join rows
    for authorship in paper.authors:
        if not authorship.person.canonical_person_id:
            continue
        author_stmt = (
            insert(PaperAuthor)
            .values(
                paper_id=paper_db_id,
                person_id=authorship.person.canonical_person_id,
                author_position=authorship.position,
                is_corresponding=authorship.is_corresponding,
            )
            .on_conflict_do_update(
                index_elements=["paper_id", "person_id"],
                set_={
                    "author_position": authorship.position,
                    "is_corresponding": authorship.is_corresponding,
                },
            )
        )
        await session.execute(author_stmt)

    return paper_db_id


async def upsert_repo(
    session: AsyncSession,
    repo: RepoRecord,
    owner_person_id: str | None = None,
    owner_org_id: str | None = None,
) -> str:
    """Upsert repo by full_name. Returns the repo's PK.

    Raises ValueError if full_name is empty — ON CONFLICT on NULL/empty never
    fires in PostgreSQL, causing phantom duplicates on re-ingest.
    """
    if not repo.full_name:
        raise ValueError("full_name is required for upsert_repo")
    stmt = (
        insert(Repo)
        .values(
            id=new_id(),
            full_name=repo.full_name,
            github_repo_id=repo.github_repo_id,
            description=repo.description,
            language=repo.language,
            stars=repo.stars,
            forks=repo.forks,
            topics=repo.topics,
            owner_person_id=owner_person_id,
            owner_org_id=owner_org_id,
        )
        .on_conflict_do_update(
            index_elements=["full_name"],
            set_={
                "description": repo.description,
                "language": repo.language,
                "stars": repo.stars,
                "forks": repo.forks,
                "topics": repo.topics,
                "github_repo_id": repo.github_repo_id,
                "owner_person_id": owner_person_id,
                "owner_org_id": owner_org_id,
            },
        )
        .returning(Repo.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def upsert_repo_contributor(
    session: AsyncSession,
    repo_id: str,
    person_id: str,
    contributions: int = 0,
) -> None:
    """Upsert a repo_contributors join row."""
    stmt = (
        insert(RepoContributor)
        .values(repo_id=repo_id, person_id=person_id, contributions=contributions)
        .on_conflict_do_update(
            index_elements=["repo_id", "person_id"],
            set_={"contributions": contributions},
        )
    )
    await session.execute(stmt)


async def upsert_entity_link(
    session: AsyncSession,
    person_id_a: str,
    person_id_b: str,
    confidence: float,
    method: str,
) -> None:
    """Upsert an entity_links candidate (canonical ordering enforced)."""
    id_a, id_b = sorted([person_id_a, person_id_b])
    stmt = (
        insert(EntityLink)
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
