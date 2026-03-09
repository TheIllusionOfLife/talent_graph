"""Builds and upserts graph nodes/edges into Neo4j using idempotent MERGE."""

from talent_graph.graph.neo4j_client import run_write_query
from talent_graph.graph.queries import (
    MERGE_AFFILIATED,
    MERGE_AUTHORED,
    MERGE_COAUTHORED,
    MERGE_CONCEPT,
    MERGE_ORG,
    MERGE_PAPER,
    MERGE_PAPER_ABOUT_CONCEPT,
    MERGE_PERSON,
)
from talent_graph.normalize.common_schema import PaperRecord


class GraphBuilder:
    """Upserts canonical records into Neo4j. All operations use MERGE (idempotent)."""

    async def upsert_paper(self, paper: PaperRecord) -> None:
        """Write a paper and all related nodes/edges to Neo4j."""
        # 1. Upsert paper node
        await run_write_query(
            MERGE_PAPER,
            {
                "paper_id": paper.openalex_work_id,
                "openalex_work_id": paper.openalex_work_id,
                "title": paper.title,
                "publication_year": paper.publication_year,
                "citation_count": paper.citation_count,
            },
        )

        # 2. Upsert concepts + ABOUT edges
        for concept in paper.concepts:
            await run_write_query(
                MERGE_CONCEPT,
                {
                    "concept_id": concept.openalex_concept_id,
                    "openalex_concept_id": concept.openalex_concept_id,
                    "name": concept.name,
                    "level": concept.level,
                },
            )
            await run_write_query(
                MERGE_PAPER_ABOUT_CONCEPT,
                {
                    "openalex_work_id": paper.openalex_work_id,
                    "openalex_concept_id": concept.openalex_concept_id,
                    "score": concept.score,
                },
            )

        # 3. Upsert persons, orgs, AUTHORED + AFFILIATED edges
        resolved_authors = [
            ap for ap in paper.authors if ap.person.canonical_person_id is not None
        ]
        for authorship in resolved_authors:
            person = authorship.person

            # Upsert org first (FK reference)
            if person.org and person.org.openalex_institution_id:
                await run_write_query(
                    MERGE_ORG,
                    {
                        "org_id": person.org.openalex_institution_id,
                        "openalex_institution_id": person.org.openalex_institution_id,
                        "name": person.org.name,
                    },
                )

            # Upsert person node
            await run_write_query(
                MERGE_PERSON,
                {
                    "person_id": person.canonical_person_id,
                    "name": person.name,
                    "openalex_author_id": person.openalex_author_id,
                    "github_login": person.github_login,
                    "orcid": person.orcid,
                },
            )

            # AFFILIATED_WITH edge
            if person.org and person.org.openalex_institution_id:
                await run_write_query(
                    MERGE_AFFILIATED,
                    {
                        "person_id": person.canonical_person_id,
                        "openalex_institution_id": person.org.openalex_institution_id,
                    },
                )

            # AUTHORED edge
            await run_write_query(
                MERGE_AUTHORED,
                {
                    "person_id": person.canonical_person_id,
                    "openalex_work_id": paper.openalex_work_id,
                    "author_position": authorship.position,
                    "is_corresponding": authorship.is_corresponding,
                },
            )

        # 4. COAUTHORED_WITH edges (undirected, between all resolved co-authors)
        for i, ap_a in enumerate(resolved_authors):
            for ap_b in resolved_authors[i + 1 :]:
                pid_a = ap_a.person.canonical_person_id
                pid_b = ap_b.person.canonical_person_id
                # Canonical ordering prevents duplicate reverse edges
                id_a, id_b = sorted([pid_a, pid_b])  # type: ignore[type-var]
                await run_write_query(
                    MERGE_COAUTHORED,
                    {"person_id_a": id_a, "person_id_b": id_b},
                )
