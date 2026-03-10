"""Integration tests for GET /discovery/{entity_type}/{entity_id}."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import ConceptFactory, PersonFactory


@pytest.mark.asyncio
async def test_discovery_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/discovery/concept/nonexistent", headers={"X-API-Key": "bad"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_discovery_seed_not_found_404(api_client: AsyncClient) -> None:
    response = await api_client.get("/discovery/concept/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_discovery_concept_ok(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    """Insert a Concept, mock neo4j returning no candidates → 200 with empty candidates."""
    async with db_session_factory() as session:
        concept = ConceptFactory.build(
            name="Machine Learning",
            openalex_concept_id="C41008148",
        )
        session.add(concept)
        await session.commit()
        concept_id = concept.id

    with (
        patch(
            "talent_graph.api.routes.discovery.encode_one_async",
            new_callable=AsyncMock,
            return_value=[0.0] * 384,
        ),
        patch(
            "talent_graph.api.routes.discovery.run_query",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await api_client.get(f"/discovery/concept/{concept_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["seed_entity_type"] == "concept"
    assert data["seed_entity_id"] == concept_id
    assert data["candidates"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["standard", "hidden", "emerging"])
async def test_discovery_modes(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
    mode: str,
) -> None:
    async with db_session_factory() as session:
        concept = ConceptFactory.build(
            name="Neural Networks",
            openalex_concept_id=f"C_mode_{mode}",
        )
        session.add(concept)
        await session.commit()
        concept_id = concept.id

    with (
        patch(
            "talent_graph.api.routes.discovery.encode_one_async",
            new_callable=AsyncMock,
            return_value=[0.0] * 384,
        ),
        patch(
            "talent_graph.api.routes.discovery.run_query",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        response = await api_client.get(f"/discovery/concept/{concept_id}?mode={mode}")

    assert response.status_code == 200
    assert response.json()["mode"] == mode


@pytest.mark.asyncio
async def test_discovery_neo4j_unavailable_503(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        concept = ConceptFactory.build(
            name="Graph Theory",
            openalex_concept_id="C_graph_theory",
        )
        session.add(concept)
        await session.commit()
        concept_id = concept.id

    with (
        patch(
            "talent_graph.api.routes.discovery.encode_one_async",
            new_callable=AsyncMock,
            return_value=[0.0] * 384,
        ),
        patch(
            "talent_graph.api.routes.discovery.run_query",
            side_effect=RuntimeError("Neo4j connection refused"),
        ),
    ):
        response = await api_client.get(f"/discovery/concept/{concept_id}")

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_discovery_person_ok(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    """Insert seed Person and candidate Person; mock neo4j returning the candidate row."""
    async with db_session_factory() as session:
        seed_person = PersonFactory.build(name="Seed Person")
        candidate_person = PersonFactory.build(name="Candidate Alice")
        session.add_all([seed_person, candidate_person])
        await session.commit()
        seed_id = seed_person.id
        candidate_id = candidate_person.id

    graph_rows = [{"person_id": candidate_id, "hops": 2}]

    with (
        patch(
            "talent_graph.api.routes.discovery.encode_one_async",
            new_callable=AsyncMock,
            return_value=[0.0] * 384,
        ),
        patch(
            "talent_graph.api.routes.discovery.run_query",
            new_callable=AsyncMock,
            return_value=graph_rows,
        ),
    ):
        response = await api_client.get(f"/discovery/person/{seed_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["seed_entity_type"] == "person"
    assert data["seed_entity_id"] == seed_id
    # The candidate should appear in results
    candidate_ids = [c["id"] for c in data["candidates"]]
    assert candidate_id in candidate_ids
