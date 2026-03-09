"""Async Neo4j client with connection pooling."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from talent_graph.config.settings import get_settings

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession]:
    driver = get_driver()
    async with driver.session(database="neo4j") as session:
        yield session


async def run_query(
    query: str,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a Cypher query and return all records as dicts."""
    async with get_session() as session:
        result = await session.run(query, parameters or {})
        return [record.data() async for record in result]


async def run_write_query(
    query: str,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a write Cypher query in a transaction."""
    async with get_session() as session:
        result = await session.execute_write(
            lambda tx: tx.run(query, parameters or {})
        )
        return [record.data() for record in result]


async def verify_connectivity() -> bool:
    """Return True if Neo4j is reachable and APOC is available."""
    try:
        rows = await run_query("RETURN apoc.version() AS version")
        return bool(rows)
    except Exception:
        return False
