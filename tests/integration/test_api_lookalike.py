"""Integration tests for GET /lookalike/{person_id}."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import PersonFactory

pytestmark = pytest.mark.asyncio


class TestLookalikeAuth:
    async def test_missing_api_key_returns_401(self, api_client: AsyncClient) -> None:
        response = await api_client.get(
            "/lookalike/some-id",
            headers={"X-API-Key": ""},
        )
        assert response.status_code == 401


class TestLookalikeNotFound:
    async def test_person_not_found(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/lookalike/nonexistent-id")
        assert response.status_code == 404


class TestLookalikeServiceError:
    async def test_search_service_unavailable(
        self,
        api_client: AsyncClient,
        db_session_factory: async_sessionmaker,
    ) -> None:
        person = PersonFactory.build(name="Dave Error", embedding=[0.1] * 384)
        async with db_session_factory() as session:
            session.add(person)
            await session.commit()
            person_id = person.id

        with patch(
            "talent_graph.api.routes.lookalike.search_similar",
            new_callable=AsyncMock,
            side_effect=Exception("boom"),
        ):
            response = await api_client.get(f"/lookalike/{person_id}")

        assert response.status_code == 503
        assert "Vector search unavailable" in response.json()["detail"]


class TestLookalikeSuccess:
    async def test_person_no_embedding(
        self,
        api_client: AsyncClient,
        db_session_factory: async_sessionmaker,
    ) -> None:
        person = PersonFactory.build(name="No Embed", embedding=None)
        async with db_session_factory() as session:
            session.add(person)
            await session.commit()
            person_id = person.id

        response = await api_client.get(f"/lookalike/{person_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["person_id"] == person_id
        assert data["results"] == []

    async def test_valid_lookalike(
        self,
        api_client: AsyncClient,
        db_session_factory: async_sessionmaker,
    ) -> None:
        person = PersonFactory.build(name="Alice Embed", embedding=[0.1] * 384)
        async with db_session_factory() as session:
            session.add(person)
            await session.commit()
            person_id = person.id

        mock_results = [
            {"id": person_id, "name": "Alice Embed", "distance": 0.0},
            {"id": "other_id", "name": "Bob Similar", "distance": 0.15},
        ]

        with patch(
            "talent_graph.api.routes.lookalike.search_similar",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            response = await api_client.get(f"/lookalike/{person_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["person_id"] == person_id
        # Self should be excluded
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == "other_id"
        assert data["results"][0]["similarity"] == pytest.approx(0.85)

    async def test_limit_param(
        self,
        api_client: AsyncClient,
        db_session_factory: async_sessionmaker,
    ) -> None:
        person = PersonFactory.build(name="Carol Limit", embedding=[0.2] * 384)
        async with db_session_factory() as session:
            session.add(person)
            await session.commit()
            person_id = person.id

        with patch(
            "talent_graph.api.routes.lookalike.search_similar",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_search:
            response = await api_client.get(f"/lookalike/{person_id}?limit=5")

        assert response.status_code == 200
        # search_similar is called with limit+1 to account for self-exclusion
        mock_search.assert_called_once()
        assert mock_search.call_args.kwargs["limit"] == 6
