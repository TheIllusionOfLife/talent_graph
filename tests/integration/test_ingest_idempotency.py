"""Integration tests for ingestion idempotency using real PostgreSQL (testcontainers).

Runs ingest twice with the same query and asserts row counts are stable.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

import talent_graph.storage.postgres as postgres_module
from talent_graph.storage.models import Base

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

OPENALEX_RESPONSE = {
    "results": [json.loads((FIXTURE_DIR / "openalex_work.json").read_text())],
    "meta": {"count": 1, "next_cursor": None},
}


@pytest.fixture(scope="module")
def postgres_url():
    """Start a real PostgreSQL container once per module (sync — no event loop needed)."""
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        sync_url = pg.get_connection_url()
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        yield async_url


@pytest.fixture
async def db_session_factory(postgres_url: str):
    """Create tables and truncate them for each test, then restore module-level factory."""
    engine = create_async_engine(postgres_url, echo=False)

    # Create all tables (idempotent via checkfirst=True)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))

    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Truncate all data tables before each test
    async with factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
        await session.commit()

    original_factory = postgres_module._session_factory
    postgres_module._session_factory = factory
    yield factory
    postgres_module._session_factory = original_factory
    await engine.dispose()


@respx.mock
@pytest.mark.asyncio
async def test_openalex_ingest_is_idempotent(db_session_factory) -> None:
    """Running the same OpenAlex ingest twice produces identical row counts."""
    from talent_graph.ingestion.jobs import ingest_openalex

    mock_builder = AsyncMock()
    mock_builder.upsert_paper = AsyncMock()

    for _ in range(2):
        respx.get("https://api.openalex.org/works").mock(
            return_value=Response(200, json=OPENALEX_RESPONSE)
        )
        with patch("talent_graph.ingestion.jobs.GraphBuilder", return_value=mock_builder):
            await ingest_openalex(
                query="attention mechanism",
                max_results=5,
                graph_builder=mock_builder,
            )

    async with db_session_factory() as session:
        papers_count = (await session.execute(text("SELECT COUNT(*) FROM papers"))).scalar()
        persons_count = (await session.execute(text("SELECT COUNT(*) FROM persons"))).scalar()
        orgs_count = (await session.execute(text("SELECT COUNT(*) FROM orgs"))).scalar()

    assert papers_count == 1, f"Expected 1 paper, got {papers_count}"
    assert persons_count == 2, f"Expected 2 persons, got {persons_count}"
    assert orgs_count == 1, f"Expected 1 org, got {orgs_count}"


@respx.mock
@pytest.mark.asyncio
async def test_github_ingest_is_idempotent(db_session_factory) -> None:
    """Running the same GitHub ingest twice produces identical row counts."""
    from talent_graph.ingestion.jobs import ingest_github

    repo_fixture = json.loads((FIXTURE_DIR / "github_repo.json").read_text())
    user_fixture = json.loads((FIXTURE_DIR / "github_user.json").read_text())
    contributors_fixture = json.loads((FIXTURE_DIR / "github_contributors.json").read_text())
    contributor1_user = {
        **user_fixture,
        "login": "contributor1",
        "name": "Contributor One",
        "email": None,
    }

    mock_builder = AsyncMock()
    mock_builder.upsert_repo = AsyncMock()

    for _ in range(2):
        respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
            return_value=Response(200, json=repo_fixture)
        )
        respx.get("https://api.github.com/repos/octocat/Hello-World/contributors").mock(
            return_value=Response(200, json=contributors_fixture)
        )
        respx.get("https://api.github.com/users/octocat").mock(
            return_value=Response(200, json=user_fixture)
        )
        respx.get("https://api.github.com/users/contributor1").mock(
            return_value=Response(200, json=contributor1_user)
        )
        with patch("talent_graph.ingestion.jobs.GraphBuilder", return_value=mock_builder):
            await ingest_github(
                repos=["octocat/Hello-World"],
                graph_builder=mock_builder,
            )

    async with db_session_factory() as session:
        repos_count = (await session.execute(text("SELECT COUNT(*) FROM repos"))).scalar()
        persons_count = (await session.execute(text("SELECT COUNT(*) FROM persons"))).scalar()

    assert repos_count == 1, f"Expected 1 repo, got {repos_count}"
    assert persons_count == 2, f"Expected 2 persons (owner + contributor), got {persons_count}"
