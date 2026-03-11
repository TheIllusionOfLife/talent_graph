"""CLI script: generate embeddings for all persons and rebuild the search index."""

import asyncio

import structlog
from sqlalchemy import text

from talent_graph.embeddings.embed_persons import embed_all_persons
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()


async def run(force: bool = False) -> None:
    embedded = await embed_all_persons(force=force)
    log.info("embed.done", embedded=embedded)

    if embedded > 0:
        async with get_db_session() as session:
            await session.execute(text("REINDEX INDEX ix_persons_embedding_ivfflat"))
        log.info("embed.reindex.done")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate person embeddings")
    parser.add_argument(
        "--force", action="store_true", help="Re-embed all persons (even those with embeddings)"
    )
    args = parser.parse_args()
    asyncio.run(run(force=args.force))


if __name__ == "__main__":
    main()
