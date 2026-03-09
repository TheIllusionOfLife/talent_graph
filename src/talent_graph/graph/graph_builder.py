"""Builds and upserts graph nodes/edges into Neo4j using idempotent MERGE.

Uses UNWIND-based batch queries to minimize Neo4j round trips.
"""

from talent_graph.graph.neo4j_client import run_write_query
from talent_graph.graph.queries import (
    MERGE_AUTHORED_BATCH,
    MERGE_COAUTHORED_BATCH,
    MERGE_CONCEPTS_BATCH,
    MERGE_CONTRIBUTED_TO_BATCH,
    MERGE_ORGS_BATCH,
    MERGE_PAPER,
    MERGE_PAPER_ABOUT_CONCEPTS_BATCH,
    MERGE_PERSONS_AND_AFFILIATED_BATCH,
    MERGE_REPO,
)
from talent_graph.normalize.common_schema import PaperRecord, RepoRecord


class GraphBuilder:
    """Upserts canonical records into Neo4j. All operations use MERGE (idempotent)."""

    async def upsert_paper(self, paper: PaperRecord) -> None:
        """Write a paper and all related nodes/edges to Neo4j in ~7 round trips."""
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

        # 2. Batch upsert concepts + ABOUT edges
        if paper.concepts:
            concepts_data = [
                {
                    "openalex_concept_id": c.openalex_concept_id,
                    "name": c.name,
                    "level": c.level,
                    "score": c.score,
                }
                for c in paper.concepts
            ]
            await run_write_query(MERGE_CONCEPTS_BATCH, {"concepts": concepts_data})
            await run_write_query(
                MERGE_PAPER_ABOUT_CONCEPTS_BATCH,
                {"openalex_work_id": paper.openalex_work_id, "concepts": concepts_data},
            )

        # 3. Resolve authors that have a canonical ID
        resolved = [ap for ap in paper.authors if ap.person.canonical_person_id is not None]
        if not resolved:
            return

        # 4. Batch upsert orgs (deduplicated)
        orgs_seen: set[str] = set()
        orgs_data: list[dict] = []
        for ap in resolved:
            org = ap.person.org
            if org and org.openalex_institution_id and org.openalex_institution_id not in orgs_seen:
                orgs_seen.add(org.openalex_institution_id)
                orgs_data.append(
                    {"openalex_institution_id": org.openalex_institution_id, "name": org.name}
                )
        if orgs_data:
            await run_write_query(MERGE_ORGS_BATCH, {"orgs": orgs_data})

        # 5. Batch upsert persons + AFFILIATED_WITH edges
        authors_data = [
            {
                "person_id": ap.person.canonical_person_id,
                "name": ap.person.name,
                "openalex_author_id": ap.person.openalex_author_id,
                "github_login": ap.person.github_login,
                "orcid": ap.person.orcid,
                "openalex_institution_id": (
                    ap.person.org.openalex_institution_id if ap.person.org else None
                ),
                "author_position": ap.position,
                "is_corresponding": ap.is_corresponding,
            }
            for ap in resolved
        ]
        await run_write_query(MERGE_PERSONS_AND_AFFILIATED_BATCH, {"authors": authors_data})

        # 6. Batch upsert AUTHORED edges
        await run_write_query(
            MERGE_AUTHORED_BATCH,
            {"openalex_work_id": paper.openalex_work_id, "authors": authors_data},
        )

        # 7. Batch upsert COAUTHORED_WITH edges (canonical ordering prevents duplicates)
        coauthor_pairs: list[dict] = []
        for i, ap_a in enumerate(resolved):
            for ap_b in resolved[i + 1 :]:
                id_a, id_b = sorted(
                    [ap_a.person.canonical_person_id, ap_b.person.canonical_person_id]
                )
                coauthor_pairs.append({"person_id_a": id_a, "person_id_b": id_b})
        if coauthor_pairs:
            await run_write_query(MERGE_COAUTHORED_BATCH, {"coauthors": coauthor_pairs})

    async def upsert_repo(
        self,
        repo: RepoRecord,
        contributor_person_ids: dict[str, int],
    ) -> None:
        """Write a Repo node and CONTRIBUTED_TO edges to Neo4j.

        Args:
            repo: Normalized repo record.
            contributor_person_ids: Mapping of canonical_person_id → contribution count.
        """
        await run_write_query(
            MERGE_REPO,
            {
                "full_name": repo.full_name,
                "github_repo_id": repo.github_repo_id,
                "description": repo.description,
                "language": repo.language,
                "stars": repo.stars,
                "topics": repo.topics,
            },
        )

        if contributor_person_ids:
            contributors_data = [
                {"person_id": pid, "contributions": count}
                for pid, count in contributor_person_ids.items()
            ]
            await run_write_query(
                MERGE_CONTRIBUTED_TO_BATCH,
                {"full_name": repo.full_name, "contributors": contributors_data},
            )
