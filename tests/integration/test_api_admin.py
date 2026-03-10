"""Integration tests for admin routes."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import EntityLinkFactory, PersonFactory

# ── stats ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stats_ok(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Stat Person")
        session.add(person)
        await session.commit()

    response = await api_client.get("/admin/stats")
    assert response.status_code == 200
    data = response.json()
    assert "person_count" in data
    assert "paper_count" in data
    assert "repo_count" in data
    assert "pending_entity_links" in data
    assert data["person_count"] >= 1


# ── ingest ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ingest_openalex_accepted(api_client: AsyncClient) -> None:
    with patch(
        "talent_graph.api.routes.admin.ingest_openalex",
        new_callable=AsyncMock,
    ):
        response = await api_client.post(
            "/admin/ingest/openalex",
            json={"query": "attention mechanism", "max_results": 10},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "message" in data


@pytest.mark.asyncio
async def test_ingest_github_accepted(api_client: AsyncClient) -> None:
    with patch(
        "talent_graph.api.routes.admin.ingest_github",
        new_callable=AsyncMock,
    ):
        response = await api_client.post(
            "/admin/ingest/github",
            json={"repos": ["octocat/Hello-World"]},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_ingest_github_invalid_slug_422(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/admin/ingest/github",
        json={"repos": ["not a valid slug!"]},
    )
    assert response.status_code == 422


# ── entity-links ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_entity_links_empty(api_client: AsyncClient) -> None:
    response = await api_client.get("/admin/entity-links")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_entity_links_pagination(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        # Need two persons with ordered IDs for the check constraint (a < b)
        p1 = PersonFactory.build(name="Person AA")
        p2 = PersonFactory.build(name="Person BB")
        p3 = PersonFactory.build(name="Person CC")
        session.add_all([p1, p2, p3])
        await session.flush()

        # Sort IDs to satisfy CheckConstraint("person_id_a < person_id_b")
        ids_ab = sorted([p1.id, p2.id])
        ids_bc = sorted([p2.id, p3.id])
        now = datetime.now(UTC).replace(tzinfo=None)
        link1 = EntityLinkFactory.build(
            person_id_a=ids_ab[0],
            person_id_b=ids_ab[1],
            created_at=now,
        )
        link2 = EntityLinkFactory.build(
            person_id_a=ids_bc[0],
            person_id_b=ids_bc[1],
            created_at=now,
        )
        session.add_all([link1, link2])
        await session.commit()

    response = await api_client.get("/admin/entity-links?page=1&page_size=1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["page_size"] == 1


@pytest.mark.asyncio
async def test_approve_entity_link(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        p1 = PersonFactory.build(name="Person X")
        p2 = PersonFactory.build(name="Person Y")
        session.add_all([p1, p2])
        await session.flush()

        ids = sorted([p1.id, p2.id])
        now = datetime.now(UTC).replace(tzinfo=None)
        link = EntityLinkFactory.build(
            person_id_a=ids[0],
            person_id_b=ids[1],
            status="pending",
            created_at=now,
        )
        session.add(link)
        await session.commit()
        link_id = link.id

    response = await api_client.post(f"/admin/entity-links/{link_id}/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "merged"
    assert data["id"] == link_id


@pytest.mark.asyncio
async def test_reject_entity_link(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        p1 = PersonFactory.build(name="Person M")
        p2 = PersonFactory.build(name="Person N")
        session.add_all([p1, p2])
        await session.flush()

        ids = sorted([p1.id, p2.id])
        now = datetime.now(UTC).replace(tzinfo=None)
        link = EntityLinkFactory.build(
            person_id_a=ids[0],
            person_id_b=ids[1],
            status="pending",
            created_at=now,
        )
        session.add(link)
        await session.commit()
        link_id = link.id

    response = await api_client.post(f"/admin/entity-links/{link_id}/reject")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"


@pytest.mark.asyncio
async def test_approve_already_merged_409(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        p1 = PersonFactory.build(name="Person P")
        p2 = PersonFactory.build(name="Person Q")
        session.add_all([p1, p2])
        await session.flush()

        ids = sorted([p1.id, p2.id])
        now = datetime.now(UTC).replace(tzinfo=None)
        link = EntityLinkFactory.build(
            person_id_a=ids[0],
            person_id_b=ids[1],
            status="merged",
            created_at=now,
        )
        session.add(link)
        await session.commit()
        link_id = link.id

    response = await api_client.post(f"/admin/entity-links/{link_id}/approve")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_entity_link_not_found_404(api_client: AsyncClient) -> None:
    response = await api_client.post("/admin/entity-links/nonexistent-id/approve")
    assert response.status_code == 404
