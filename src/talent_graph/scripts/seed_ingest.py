"""CLI script: seed the database with sample data from OpenAlex or GitHub."""

import argparse
import asyncio

import structlog

from talent_graph.ingestion.jobs import ingest_openalex

log = structlog.get_logger()


async def run(source: str, query: str, max_results: int) -> None:
    if source == "openalex":
        counts = await ingest_openalex(query=query, max_results=max_results)
        log.info("seed.done", source=source, **counts)
    else:
        raise NotImplementedError(f"Source '{source}' not yet implemented (Sprint 2)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Talent Graph with public data")
    parser.add_argument(
        "--source",
        choices=["openalex", "github"],
        default="openalex",
        help="Data source to ingest",
    )
    parser.add_argument("--query", default="multimodal dialogue", help="Search query")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum records to ingest")
    args = parser.parse_args()
    asyncio.run(run(source=args.source, query=args.query, max_results=args.max_results))


if __name__ == "__main__":
    main()
