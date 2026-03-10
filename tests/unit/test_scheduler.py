"""Unit tests for the ingestion scheduler."""

import os
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_pipeline_phases_are_independent() -> None:
    """OpenAlex failure must not abort GitHub ingestion."""
    github_mock = AsyncMock(return_value={"persons": 1})

    with (
        patch(
            "talent_graph.scripts.scheduler.ingest_openalex",
            side_effect=RuntimeError("openalex down"),
        ),
        patch(
            "talent_graph.scripts.scheduler.ingest_github",
            github_mock,
        ),
    ):
        from talent_graph.scripts.scheduler import run_ingestion_pipeline

        await run_ingestion_pipeline()

    github_mock.assert_awaited_once()


def test_scheduler_disabled_exits_early() -> None:
    """When SCHEDULER_ENABLED=false, main() returns without starting the scheduler."""
    os.environ["SCHEDULER_ENABLED"] = "false"

    try:
        from talent_graph.config.settings import get_settings

        get_settings.cache_clear()  # type: ignore[attr-defined]

        with patch("talent_graph.scripts.scheduler.AsyncIOScheduler") as mock_scheduler_cls:
            from talent_graph.scripts.scheduler import main

            main()
            mock_scheduler_cls.assert_not_called()
    finally:
        os.environ.pop("SCHEDULER_ENABLED", None)
        from talent_graph.config.settings import get_settings

        get_settings.cache_clear()  # type: ignore[attr-defined]
