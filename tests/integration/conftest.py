"""Shared fixtures for integration tests."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

import talent_graph.storage.postgres as postgres_module
from talent_graph.storage.models import Base

TEST_API_KEY = "test-key"
HEADERS = {"X-API-Key": TEST_API_KEY}


# ── Testcontainer — runs once for the whole session (sync fixture) ─────────────


@pytest.fixture(scope="session")
def postgres_container():
    """Start a single Postgres container for the test session."""
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        yield pg


@pytest.fixture(scope="session")
def postgres_url(postgres_container: PostgresContainer) -> str:
    """Return the async DB URL for the session-scoped testcontainer."""
    sync_url = postgres_container.get_connection_url()
    return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)


# ── Per-test DB fixtures — engine created fresh in the test's event loop ───────


@pytest_asyncio.fixture
async def db_session_factory(postgres_url: str) -> AsyncIterator[async_sessionmaker]:
    """Per-test: create async engine in test loop, ensure schema, truncate all tables.

    Creating the engine per test (not session) is the only safe approach with asyncpg:
    asyncpg connections are bound to the event loop that created them.  Using a
    session-scoped engine across per-function loops causes
    "Future attached to a different loop" errors.
    """
    engine = create_async_engine(postgres_url, echo=False)

    # Ensure schema + pgvector extension exist (checkfirst=True is idempotent)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))

    # Wipe all rows in one atomic statement — no per-table loop, no pipelining issues
    async with engine.begin() as conn:
        table_names = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))

    factory = async_sessionmaker(engine, expire_on_commit=False)
    original = postgres_module._session_factory
    postgres_module._session_factory = factory
    yield factory
    postgres_module._session_factory = original
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(db_session_factory: async_sessionmaker) -> AsyncIterator[AsyncClient]:
    """httpx AsyncClient with ASGI transport; Neo4j/prestige/neo4j-close mocked."""
    from talent_graph.api.main import create_app

    with (
        patch("talent_graph.api.main.run_write_query", new_callable=AsyncMock),
        patch(
            "talent_graph.api.main.init_prestige_names",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("talent_graph.api.main.close_driver", new_callable=AsyncMock),
        # Patch where imported so the health route sees the mock
        patch(
            "talent_graph.api.routes.health.verify_connectivity",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers=HEADERS,
        ) as client:
            yield client


@pytest_asyncio.fixture
async def db_session(db_session_factory: async_sessionmaker):
    """Convenience fixture: open a single DB session for test data setup."""
    async with db_session_factory() as session:
        yield session
