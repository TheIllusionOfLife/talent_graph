"""End-to-end flow test: ingest via DB → GET person → search → discovery."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import OrgFactory, PaperFactory, PersonFactory


@pytest.mark.asyncio
async def test_e2e_full_flow(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    """
    1. Insert Org, Person (with embedding), Paper via DB session.
    2. GET /person/{id} → verify PersonDetail.
    3. GET /search?q=... (mocked encode + mocked vector store) → verify result includes person.
    4. GET /discovery/person/{id} (mocked neo4j) → verify candidates list.
    """
    # ── 1. Seed data via DB ──────────────────────────────────────────────────
    zero_vec = [0.0] * 384

    async with db_session_factory() as session:
        org = OrgFactory.build(name="MIT", country_code="US", type="education")
        person = PersonFactory.build(
            name="Alice Researcher",
            org_id=org.id,
            embedding=zero_vec,
        )
        paper = PaperFactory.build(
            title="Attention Is All You Need",
            publication_year=2017,
            citation_count=50000,
            concepts=["Machine Learning", "Transformers"],
        )
        session.add_all([org, person, paper])
        await session.flush()

        # Associate paper with person via paper_authors join table
        from talent_graph.storage.models import PaperAuthor

        session.add(
            PaperAuthor(
                paper_id=paper.id,
                person_id=person.id,
                author_position=1,
                is_corresponding=True,
            )
        )
        await session.commit()
        person_id = person.id

    # ── 2. GET /person/{id} ──────────────────────────────────────────────────
    response = await api_client.get(f"/person/{person_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == person_id
    assert detail["name"] == "Alice Researcher"
    assert detail["org"]["name"] == "MIT"
    assert len(detail["papers"]) == 1
    assert detail["papers"][0]["title"] == "Attention Is All You Need"
    assert detail["papers"][0]["citation_count"] == 50000

    # ── 3. GET /search?q=... ─────────────────────────────────────────────────
    mock_rows = [{"id": person_id, "name": "Alice Researcher", "distance": 0.05}]

    with (
        patch(
            "talent_graph.api.routes.search.encode_one_async",
            new_callable=AsyncMock,
            return_value=zero_vec,
        ),
        patch(
            "talent_graph.storage.vector_store.search_similar",
            new_callable=AsyncMock,
            return_value=mock_rows,
        ),
    ):
        search_resp = await api_client.get("/search?q=attention+transformer")

    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["query"] == "attention+transformer"
    result_ids = [r["id"] for r in search_data["results"]]
    assert person_id in result_ids

    # ── 4. GET /discovery/person/{id} ────────────────────────────────────────
    # Seed a second person who will appear as a candidate
    async with db_session_factory() as session:
        candidate = PersonFactory.build(name="Bob Candidate")
        session.add(candidate)
        await session.commit()
        candidate_id = candidate.id

    graph_rows = [{"person_id": candidate_id, "hops": 1}]

    with (
        patch(
            "talent_graph.api.routes.discovery.encode_one_async",
            new_callable=AsyncMock,
            return_value=zero_vec,
        ),
        patch(
            "talent_graph.api.routes.discovery.run_query",
            new_callable=AsyncMock,
            return_value=graph_rows,
        ),
    ):
        discovery_resp = await api_client.get(f"/discovery/person/{person_id}")

    assert discovery_resp.status_code == 200
    discovery_data = discovery_resp.json()
    assert discovery_data["seed_entity_type"] == "person"
    assert discovery_data["seed_entity_id"] == person_id
    candidate_ids = [c["id"] for c in discovery_data["candidates"]]
    assert candidate_id in candidate_ids

    # Verify candidate shape
    candidate_result = next(c for c in discovery_data["candidates"] if c["id"] == candidate_id)
    assert "score" in candidate_result
    assert "breakdown" in candidate_result
    assert "hop_distance" in candidate_result
    assert candidate_result["hop_distance"] == 1
