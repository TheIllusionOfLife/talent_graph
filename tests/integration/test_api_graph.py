"""Integration tests for GET /graph/ego/{node_type}/{node_id}."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import PersonFactory

pytestmark = pytest.mark.asyncio


class TestEgoGraphAuth:
    """Auth: 401 without API key."""

    async def test_missing_api_key_returns_401(self, api_client: AsyncClient) -> None:
        response = await api_client.get(
            "/graph/ego/person/some-id",
            headers={"X-API-Key": "bad"},
        )
        assert response.status_code == 401


class TestEgoGraphNotFound:
    """404 when seed entity does not exist in Postgres."""

    async def test_person_not_found(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/graph/ego/person/nonexistent-id")
        assert response.status_code == 404


class TestEgoGraphValidation:
    """Parameter validation."""

    async def test_invalid_node_type(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/graph/ego/invalid_type/some-id")
        assert response.status_code == 422

    async def test_hops_too_large(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/graph/ego/person/some-id?hops=5")
        assert response.status_code == 422

    async def test_hops_zero(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/graph/ego/person/some-id?hops=0")
        assert response.status_code == 422

    async def test_node_limit_too_large(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/graph/ego/person/some-id?node_limit=500")
        assert response.status_code == 422


class TestEgoGraphSuccess:
    """200 with mocked Neo4j for valid requests."""

    async def test_valid_person_ego_graph(
        self,
        api_client: AsyncClient,
        db_session_factory: async_sessionmaker,
    ) -> None:
        # Seed a person in Postgres
        person = PersonFactory.build(name="Alice Graph")
        async with db_session_factory() as session:
            session.add(person)
            await session.commit()
            person_id = person.id

        neo4j_result = [
            {
                "nodes": [
                    {
                        "type": "Person",
                        "node_key": person_id,
                        "label": person.name,
                        "props": {"person_id": person_id, "name": person.name},
                    },
                    {
                        "type": "Paper",
                        "node_key": "W123",
                        "label": "Test Paper",
                        "props": {
                            "openalex_work_id": "W123",
                            "title": "Test Paper",
                            "citation_count": 5,
                        },
                    },
                ],
                "links": [
                    {
                        "source_type": "Person",
                        "source_key": person_id,
                        "target_type": "Paper",
                        "target_key": "W123",
                        "rel_type": "AUTHORED",
                    },
                ],
                "truncated": False,
            }
        ]

        with patch(
            "talent_graph.api.routes.graph.run_query",
            new_callable=AsyncMock,
            return_value=neo4j_result,
        ):
            response = await api_client.get(f"/graph/ego/person/{person_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["center_id"] == f"person__{person_id}"
        assert len(data["nodes"]) == 2
        assert len(data["links"]) == 1
        assert data["truncated"] is False

    async def test_empty_neo4j_result(
        self,
        api_client: AsyncClient,
        db_session_factory: async_sessionmaker,
    ) -> None:
        person = PersonFactory.build(name="Bob Empty")
        async with db_session_factory() as session:
            session.add(person)
            await session.commit()
            person_id = person.id

        neo4j_result = [{"nodes": [], "links": [], "truncated": False}]

        with patch(
            "talent_graph.api.routes.graph.run_query",
            new_callable=AsyncMock,
            return_value=neo4j_result,
        ):
            response = await api_client.get(f"/graph/ego/person/{person_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 0
        assert len(data["links"]) == 0

    async def test_custom_hops_param(
        self,
        api_client: AsyncClient,
        db_session_factory: async_sessionmaker,
    ) -> None:
        person = PersonFactory.build(name="Carol Hops")
        async with db_session_factory() as session:
            session.add(person)
            await session.commit()
            person_id = person.id

        neo4j_result = [{"nodes": [], "links": [], "truncated": False}]

        with patch(
            "talent_graph.api.routes.graph.run_query",
            new_callable=AsyncMock,
            return_value=neo4j_result,
        ) as mock_query:
            response = await api_client.get(f"/graph/ego/person/{person_id}?hops=3")

        assert response.status_code == 200
        mock_query.assert_called_once()
        # Verify hops=3 was interpolated into the Cypher query
        query_str = mock_query.call_args[0][0]
        assert "[*1..3]" in query_str
