"""CLI script: seed the database with sample data from OpenAlex and GitHub."""

import argparse
import asyncio

import structlog
from sqlalchemy import text

from talent_graph.anomaly.hidden_expert import compute_hidden_expert_scores
from talent_graph.embeddings.embed_persons import embed_all_persons
from talent_graph.ingestion.jobs import ingest_github, ingest_openalex
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()

# Default GitHub repos to ingest alongside the OpenAlex query
_DEFAULT_GITHUB_REPOS = [
    "huggingface/transformers",
    "openai/whisper",
]


async def run(
    source: str,
    query: str,
    max_results: int,
    github_repos: list[str],
    skip_embeddings: bool,
    skip_anomaly: bool,
) -> None:
    if source in ("openalex", "all"):
        counts = await ingest_openalex(query=query, max_results=max_results)
        log.info("seed.openalex.done", **counts)

    if source in ("github", "all"):
        gh_counts = await ingest_github(repos=github_repos)
        log.info("seed.github.done", **gh_counts)

    if not skip_embeddings:
        embedded = await embed_all_persons()
        log.info("seed.embeddings.done", embedded=embedded)

        # Rebuild IVFFlat index for good recall after bulk inserts.
        # (The index was created on an empty table at migration time.)
        # Note: REINDEX INDEX CONCURRENTLY cannot run inside a transaction block,
        # so we use regular REINDEX INDEX here (safe for dev/seed contexts).
        async with get_db_session() as session:
            await session.execute(text("REINDEX INDEX ix_persons_embedding_ivfflat"))
        log.info("seed.embeddings.reindex.done")

    if not skip_anomaly:
        scored = await compute_hidden_expert_scores()
        log.info("seed.anomaly.done", scored=scored)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Talent Graph with public data")
    parser.add_argument(
        "--source",
        choices=["openalex", "github", "all"],
        default="all",
        help="Data source to ingest (default: all)",
    )
    parser.add_argument("--query", default="multimodal dialogue", help="OpenAlex search query")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum OpenAlex records")
    parser.add_argument(
        "--github-repos",
        nargs="*",
        default=_DEFAULT_GITHUB_REPOS,
        help="GitHub 'owner/repo' slugs to ingest",
    )
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embedding generation (useful for quick re-runs)",
    )
    parser.add_argument(
        "--skip-anomaly",
        action="store_true",
        help="Skip hidden expert score computation",
    )
    args = parser.parse_args()
    asyncio.run(
        run(
            source=args.source,
            query=args.query,
            max_results=args.max_results,
            github_repos=args.github_repos,
            skip_embeddings=args.skip_embeddings,
            skip_anomaly=args.skip_anomaly,
        )
    )


if __name__ == "__main__":
    main()
