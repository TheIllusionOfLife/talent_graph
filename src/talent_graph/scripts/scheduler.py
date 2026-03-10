"""Standalone ingestion scheduler — runs as a separate process (not inside uvicorn).

Start with:  python -m talent_graph.scripts.scheduler
Or via entry point:  talent-graph-scheduler

Design notes:
- Separate process avoids duplicate jobs in multi-worker uvicorn deployments.
- AsyncIOScheduler matches the async ingest_* job functions.
- max_instances=1 prevents overlapping runs if ingestion takes longer than interval.
- misfire_grace_time=300 runs a misfired job if it fired ≤5 min late.
- Independent try/except per phase: OpenAlex failure does not abort GitHub ingestion.
- SCHEDULER_ENABLED=false lets operators disable without redeploying.
"""

import asyncio
import signal
import sys

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from talent_graph.config.settings import get_settings
from talent_graph.ingestion.jobs import ingest_github, ingest_openalex

log = structlog.get_logger()


async def run_ingestion_pipeline() -> None:
    """Run one full ingestion cycle: OpenAlex then GitHub (independent phases)."""
    settings = get_settings()
    log.info("scheduler.pipeline.start")

    try:
        stats = await ingest_openalex(
            query=settings.scheduler_openalex_query,
            max_results=settings.scheduler_openalex_max_results,
        )
        log.info("scheduler.openalex.done", stats=stats)
    except Exception as exc:
        log.error("scheduler.openalex.failed", error=str(exc))

    try:
        stats = await ingest_github(repos=settings.scheduler_github_repos)
        log.info("scheduler.github.done", stats=stats)
    except Exception as exc:
        log.error("scheduler.github.failed", error=str(exc))

    log.info("scheduler.pipeline.done")


def main() -> None:
    settings = get_settings()

    if not settings.scheduler_enabled:
        log.info("scheduler.disabled")
        return

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_ingestion_pipeline,
        trigger="interval",
        hours=settings.scheduler_interval_hours,
        max_instances=1,
        misfire_grace_time=300,
        id="ingestion_pipeline",
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig: int, _frame: object) -> None:
        log.info("scheduler.shutdown", signal=sig)
        scheduler.shutdown(wait=False)
        loop.stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    scheduler.start()
    log.info("scheduler.started", interval_hours=settings.scheduler_interval_hours)

    try:
        loop.run_forever()
    finally:
        loop.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
