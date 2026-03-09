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
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from testcontainers.postgres import PostgresContainer

import talent_graph.storage.postgres as postgres_module
from talent_graph.storage.models import Base

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

# Two identical work responses: running ingest twice should produce the same counts
OPENALEX_RESPONSE = {
    "results": [json.loads((FIXTURE_DIR / "openalex_work.json").read_text())],
    "meta": {"count": 1, "next_cursor": None},
}


@pytest.fixture(scope="module")
def postgres_url():
    """Start a real PostgreSQL container for the module, yield the asyncpg URL."""
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        # testcontainers returns a sync psycopg2-style URL; swap driver for asyncpg
        sync_url = pg.get_connection_url()
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        yield async_url


@pytest.fixture(scope="module")
async def migrated_db(postgres_url: str):
    """Create tables via SQLAlchemy metadata (faster than running Alembic in tests)."""
    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def clean_session_factory(migrated_db, postgres_url: str):
    """
    Override the module-level _session_factory to point at the test container.
    Resets between tests so each test starts with isolated data.
    """
    engine = migrated_db
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Truncate all tables before each test
    async with factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
        await session.commit()

    original_factory = postgres_module._session_factory
    postgres_module._session_factory = factory
    yield factory
    postgres_module._session_factory = original_factory


@respx.mock
@pytest.mark.asyncio
async def test_openalex_ingest_is_idempotent(clean_session_factory) -> None:
    """Running the same OpenAlex ingest twice produces identical row counts."""
    from talent_graph.ingestion.jobs import ingest_openalex

    # Mock OpenAlex API — same response for any page
    respx.get("https://api.openalex.org/works").mock(
        return_value=Response(200, json=OPENALEX_RESPONSE)
    )

    # Mock Neo4j GraphBuilder so we don't need a Neo4j container
    mock_builder = AsyncMock()
    mock_builder.upsert_paper = AsyncMock()

    with patch("talent_graph.ingestion.jobs.GraphBuilder", return_value=mock_builder):
        await ingest_openalex(
            query="attention mechanism",
            max_results=5,
            graph_builder=mock_builder,
        )

    # Re-mock for second run (respx mock is consumed, re-register)
    respx.get("https://api.openalex.org/works").mock(
        return_value=Response(200, json=OPENALEX_RESPONSE)
    )

    with patch("talent_graph.ingestion.jobs.GraphBuilder", return_value=mock_builder):
        await ingest_openalex(
            query="attention mechanism",
            max_results=5,
            graph_builder=mock_builder,
        )

    # Assert counts are identical (idempotent)
    async with clean_session_factory() as session:
        papers_count = (await session.execute(text("SELECT COUNT(*) FROM papers"))).scalar()
        persons_count = (await session.execute(text("SELECT COUNT(*) FROM persons"))).scalar()
        orgs_count = (await session.execute(text("SELECT COUNT(*) FROM orgs"))).scalar()

    assert papers_count == 1, f"Expected 1 paper, got {papers_count}"
    assert persons_count == 2, f"Expected 2 persons, got {persons_count}"
    assert orgs_count == 1, f"Expected 1 org, got {orgs_count}"


@respx.mock
@pytest.mark.asyncio
async def test_github_ingest_is_idempotent(clean_session_factory) -> None:
    """Running the same GitHub ingest twice produces identical row counts."""
    from talent_graph.ingestion.jobs import ingest_github

    repo_fixture = json.loads((FIXTURE_DIR / "github_repo.json").read_text())
    user_fixture = json.loads((FIXTURE_DIR / "github_user.json").read_text())
    contributors_fixture = json.loads((FIXTURE_DIR / "github_contributors.json").read_text())

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
        return_value=Response(200, json={**user_fixture, "login": "contributor1", "name": "Contributor One", "email": None})
    )

    mock_builder = AsyncMock()
    mock_builder.upsert_repo = AsyncMock()

    with patch("talent_graph.ingestion.jobs.GraphBuilder", return_value=mock_builder):
        await ingest_github(
            repos=["octocat/Hello-World"],
            graph_builder=mock_builder,
        )

    # Re-register mocks for second run
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
        return_value=Response(200, json={**user_fixture, "login": "contributor1", "name": "Contributor One", "email": None})
    )

    with patch("talent_graph.ingestion.jobs.GraphBuilder", return_value=mock_builder):
        await ingest_github(
            repos=["octocat/Hello-World"],
            graph_builder=mock_builder,
        )

    async with clean_session_factory() as session:
        repos_count = (await session.execute(text("SELECT COUNT(*) FROM repos"))).scalar()
        persons_count = (await session.execute(text("SELECT COUNT(*) FROM persons"))).scalar()

    assert repos_count == 1, f"Expected 1 repo, got {repos_count}"
    assert persons_count == 2, f"Expected 2 persons (owner + contributor), got {persons_count}"
