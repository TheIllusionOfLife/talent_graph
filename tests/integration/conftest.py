"""Shared fixtures for integration tests."""

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


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("pgvector/pgvector:pg17") as pg:
        yield pg


@pytest.fixture(scope="session")
def postgres_url(postgres_container):
    sync_url = postgres_container.get_connection_url()
    return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_url):
    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(db_engine):
    """Per-test: truncate all tables, override session factory, yield."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
        await session.commit()
    original = postgres_module._session_factory
    postgres_module._session_factory = factory
    yield factory
    postgres_module._session_factory = original


@pytest_asyncio.fixture
async def api_client(db_session_factory):
    """httpx AsyncClient with ASGI transport, mocked Neo4j and prestige init."""
    from talent_graph.api.main import create_app

    with (
        patch("talent_graph.api.main.run_write_query", new_callable=AsyncMock),
        patch(
            "talent_graph.api.main.init_prestige_names",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("talent_graph.api.main.close_driver", new_callable=AsyncMock),
        # Patch where imported (not where defined) so health route sees mocked value
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
async def db_session(db_session_factory):
    """Direct DB session for test data setup."""
    async with db_session_factory() as session:
        yield session
