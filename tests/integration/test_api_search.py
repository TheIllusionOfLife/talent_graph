"""Integration tests for GET /search."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import PersonFactory


@pytest.mark.asyncio
async def test_search_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/search?q=machine+learning", headers={"X-API-Key": "bad"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_empty_query_422(api_client: AsyncClient) -> None:
    """q with length 0 should be rejected by FastAPI validation (min_length=1)."""
    response = await api_client.get("/search?q=")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_returns_results(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    """With a mocked encoder and vector store, /search returns SearchResponse."""
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Alice Smith")
        session.add(person)
        await session.commit()
        person_id = person.id

    mock_rows = [{"id": person_id, "name": "Alice Smith", "distance": 0.1}]

    with (
        patch(
            "talent_graph.api.routes.search.encode_one_async",
            new_callable=AsyncMock,
            return_value=[0.0] * 384,
        ),
        patch(
            "talent_graph.api.routes.search.search_similar",
            new_callable=AsyncMock,
            return_value=mock_rows,
        ),
    ):
        response = await api_client.get("/search?q=machine+learning")

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "machine learning"
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == person_id
    assert data["results"][0]["name"] == "Alice Smith"
    assert "score" in data["results"][0]


@pytest.mark.asyncio
async def test_search_empty_results(api_client: AsyncClient) -> None:
    """With no persons in DB and mocked vector store returning empty list, results=[]."""
    with (
        patch(
            "talent_graph.api.routes.search.encode_one_async",
            new_callable=AsyncMock,
            return_value=[0.0] * 384,
        ),
        patch(
            "talent_graph.api.routes.search.search_similar",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await api_client.get("/search?q=unknown+topic")

    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
