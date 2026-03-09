"""SQLAlchemy upsert helpers (ON CONFLICT DO UPDATE — idempotent)."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from talent_graph.normalize.common_schema import (
    ConceptRecord,
    OrgRecord,
    PaperRecord,
    PersonRecord,
)
from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import Concept, Org, Paper, PaperAuthor, Person


async def upsert_org(session: AsyncSession, org: OrgRecord) -> str:
    """Upsert org by openalex_institution_id. Returns the org's PK."""
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
            set_={"name": org.name, "country_code": org.country_code},
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
            },
        )
        .returning(Person.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def upsert_concept(session: AsyncSession, concept: ConceptRecord) -> str:
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
                set_={"author_position": authorship.position},
            )
        )
        await session.execute(author_stmt)

    return paper_db_id
