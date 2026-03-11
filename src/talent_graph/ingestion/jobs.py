"""Ingestion job orchestrators — fetch → normalize → resolve → persist."""

import hashlib
import json

import structlog

from talent_graph.config.settings import get_settings
from talent_graph.entity_resolution.resolver import resolve_person, write_heuristic_links
from talent_graph.graph.graph_builder import GraphBuilder
from talent_graph.ingestion.github_client import GitHubClient
from talent_graph.ingestion.openalex_client import OpenAlexClient
from talent_graph.normalize.normalize_github import normalize_github_user, normalize_repo
from talent_graph.normalize.normalize_openalex import normalize_work
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.raw_store import RawStore
from talent_graph.storage.upsert import (
    upsert_concept,
    upsert_org,
    upsert_paper,
    upsert_person,
    upsert_repo,
    upsert_repo_contributor,
)

log = structlog.get_logger()


def _work_id(raw_work: dict, fallback_index: int) -> str:
    """Extract stable work ID from raw response; use content-hash fallback."""
    raw_id: str = raw_work.get("id", "")
    if raw_id:
        return raw_id.split("/")[-1]
    content_hash = hashlib.sha1(
        json.dumps(raw_work, sort_keys=True).encode(), usedforsecurity=False
    ).hexdigest()[:12]
    return f"noid_{content_hash}"


async def ingest_openalex(
    query: str,
    max_results: int = 200,
    raw_store: RawStore | None = None,
    graph_builder: GraphBuilder | None = None,
) -> dict[str, int]:
    """
    Full OpenAlex ingestion pipeline:
      fetch → save raw → normalize → resolve → upsert postgres → upsert neo4j

    Returns counts of upserted entities.
    """
    settings = get_settings()
    store = raw_store or RawStore()
    builder = graph_builder or GraphBuilder()

    counts = {"papers": 0, "persons": 0, "orgs": 0, "concepts": 0}

    async with OpenAlexClient(email=settings.openalex_email) as client:
        log.info("openalex.fetch.start", query=query, max_results=max_results)
        raw_works = await client.get_works_paginated(query=query, max_results=max_results)
        log.info("openalex.fetch.done", count=len(raw_works))

    for i, raw_work in enumerate(raw_works):
        work_id = _work_id(raw_work, i)
        store.save("openalex", "works", work_id, raw_work)

        paper = normalize_work(raw_work)

        if not paper.openalex_work_id:
            log.warning("openalex.work.skipped", reason="missing_id", raw_id=work_id)
            continue

        # Upsert to Postgres (single transaction per paper)
        async with get_db_session() as session:
            # Orgs first
            orgs_seen: set[str] = set()
            for authorship in paper.authors:
                org = authorship.person.org
                if (
                    org
                    and org.openalex_institution_id
                    and org.openalex_institution_id not in orgs_seen
                ):
                    orgs_seen.add(org.openalex_institution_id)
                    await upsert_org(session, org)
                    counts["orgs"] += 1

            # Resolve and upsert persons; write heuristic links AFTER upsert (FK safety)
            persons_seen: set[str] = set()
            resolved_persons = []
            for authorship in paper.authors:
                person = authorship.person
                canon_id = await resolve_person(session, person)
                if canon_id not in persons_seen:
                    persons_seen.add(canon_id)
                    await upsert_person(session, person)
                    counts["persons"] += 1
                    resolved_persons.append(person)

            for person in resolved_persons:
                await write_heuristic_links(session, person)

            # Concepts
            for concept in paper.concepts:
                await upsert_concept(session, concept)
                counts["concepts"] += 1

            # Paper + PaperAuthor join rows
            await upsert_paper(session, paper)
            counts["papers"] += 1

        # Upsert to Neo4j — eventual consistency acceptable (MERGE is idempotent)
        try:
            await builder.upsert_paper(paper)
        except Exception as neo4j_exc:
            log.warning(
                "neo4j.upsert.failed",
                openalex_work_id=paper.openalex_work_id,
                error=str(neo4j_exc),
            )

    log.info("openalex.ingest.done", **counts)
    return counts


async def ingest_github(
    repos: list[str],
    raw_store: RawStore | None = None,
    graph_builder: GraphBuilder | None = None,
    max_contributors: int = 30,
) -> dict[str, int]:
    """Full GitHub ingestion pipeline for a list of 'owner/repo' slugs.

    Pipeline: fetch → save raw → normalize → resolve → upsert postgres → upsert neo4j.

    Entity resolution runs BEFORE any upsert to prevent duplicate Person nodes.

    Args:
        repos: List of 'owner/repo' slugs to ingest.
        raw_store: Optional raw JSON store (default: new RawStore).
        graph_builder: Optional Neo4j graph builder (default: new GraphBuilder).
        max_contributors: Maximum contributors per repo (default 30). Contributors
            are already sorted by contribution count from the GitHub API; only the
            top N are kept to prevent noise from low-activity contributors.

    Returns:
        Counts of upserted entities (repos, persons).
    """
    settings = get_settings()
    store = raw_store or RawStore()
    builder = graph_builder or GraphBuilder()

    counts = {"repos": 0, "persons": 0}

    async with GitHubClient(token=settings.github_token) as gh:
        for repo_slug in repos:
            if "/" not in repo_slug:
                log.warning("github.repo.invalid_slug", slug=repo_slug, reason="missing '/'")
                continue
            owner, repo_name = repo_slug.split("/", 1)
            if not owner or not repo_name:
                log.warning(
                    "github.repo.invalid_slug", slug=repo_slug, reason="empty owner or repo"
                )
                continue

            # 1. Fetch raw data
            raw_repo = await gh.get_repo(owner, repo_name)
            raw_contributors = await gh.get_contributors(owner, repo_name, exclude_bots=True)

            # Limit contributors to top-N by contribution count (already sorted desc)
            if len(raw_contributors) > max_contributors:
                log.info(
                    "github.contributors.limited",
                    repo=repo_slug,
                    total=len(raw_contributors),
                    kept=max_contributors,
                )
                raw_contributors = raw_contributors[:max_contributors]

            # Fetch user profiles for contributors (owner + contributors).
            # Skip the owner if it is a GitHub Organization — org accounts are not Person nodes.
            owner_type = (raw_repo.get("owner") or {}).get("type", "User")
            contributor_logins = [c["login"] for c in raw_contributors]
            logins_to_fetch: set[str] = set(contributor_logins)
            if owner_type != "Organization":
                logins_to_fetch.add(owner)
            raw_users: dict[str, dict] = {}
            for login in logins_to_fetch:
                try:
                    raw_users[login] = await gh.get_user(login)
                except Exception as exc:
                    log.warning("github.user.fetch_failed", login=login, error=str(exc))

            # 2. Save raw JSON
            store.save("github", "repos", repo_slug.replace("/", "_"), raw_repo)
            for login, raw_user in raw_users.items():
                store.save("github", "users", login, raw_user)

            # 3. Normalize
            repo_record = normalize_repo(raw_repo, contributors=raw_contributors)
            person_records = {
                login: normalize_github_user(raw_user) for login, raw_user in raw_users.items()
            }

            # 4. Resolve + upsert persons; write heuristic links AFTER upsert (FK safety)
            async with get_db_session() as session:
                login_to_canon_id: dict[str, str] = {}
                persons_seen: set[str] = set()
                resolved_persons = []
                for login, person in person_records.items():
                    canon_id = await resolve_person(session, person)
                    login_to_canon_id[login] = canon_id
                    if canon_id not in persons_seen:
                        persons_seen.add(canon_id)
                        await upsert_person(session, person)
                        counts["persons"] += 1
                        resolved_persons.append(person)

                for person in resolved_persons:
                    await write_heuristic_links(session, person)

                # 5. Upsert repo
                owner_person_id = login_to_canon_id.get(owner)
                repo_db_id = await upsert_repo(
                    session,
                    repo_record,
                    owner_person_id=owner_person_id,
                    raw_metadata=raw_repo,
                )
                counts["repos"] += 1

                # 6. Upsert repo_contributors join rows
                contributions_by_login = {c["login"]: c["contributions"] for c in raw_contributors}
                for login in repo_record.contributor_logins:
                    if login in login_to_canon_id:
                        await upsert_repo_contributor(
                            session,
                            repo_id=repo_db_id,
                            person_id=login_to_canon_id[login],
                            contributions=contributions_by_login.get(login, 0),
                        )

            # 7. Upsert to Neo4j (pass person info so Person nodes get created)
            try:
                contributor_info = {
                    login_to_canon_id[login]: {
                        "contributions": contributions_by_login.get(login, 0),
                        "name": person_records[login].name if login in person_records else "",
                        "github_login": login,
                    }
                    for login in repo_record.contributor_logins
                    if login in login_to_canon_id
                }
                await builder.upsert_repo(repo_record, contributor_info)
            except Exception as neo4j_exc:
                log.warning(
                    "neo4j.repo.upsert.failed",
                    repo=repo_slug,
                    error=str(neo4j_exc),
                )

    log.info("github.ingest.done", **counts)
    return counts
