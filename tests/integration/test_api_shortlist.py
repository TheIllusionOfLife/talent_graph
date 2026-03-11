"""Integration tests for shortlist CRUD routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import PersonFactory

# ── helpers ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def _make_client(
    db_session_factory: async_sessionmaker,
    api_key: str,  # noqa: ARG001
) -> AsyncIterator[AsyncClient]:
    """Async context manager that creates a test client with the given API key."""
    from talent_graph.api.main import create_app

    with (
        patch("talent_graph.api.main.run_write_query", new_callable=AsyncMock),
        patch(
            "talent_graph.api.main.init_prestige_names",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("talent_graph.api.main.close_driver", new_callable=AsyncMock),
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
            headers={"X-API-Key": api_key},
        ) as client:
            yield client


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_shortlist(api_client: AsyncClient) -> None:
    response = await api_client.post("/shortlists", json={"name": "My List"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My List"
    assert "id" in data
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_shortlists(api_client: AsyncClient) -> None:
    await api_client.post("/shortlists", json={"name": "List A"})
    await api_client.post("/shortlists", json={"name": "List B"})

    response = await api_client.get("/shortlists")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {item["name"] for item in data}
    assert names == {"List A", "List B"}
    for item in data:
        assert "item_count" in item


@pytest.mark.asyncio
async def test_list_shortlists_own_only(
    db_session_factory: async_sessionmaker,
) -> None:
    """Key A creates a shortlist; key B sees an empty list."""
    async with _make_client(db_session_factory, api_key="test-key") as ca:
        resp = await ca.post("/shortlists", json={"name": "Owner A list"})
        assert resp.status_code == 201

    async with _make_client(db_session_factory, api_key="other-key") as cb:
        resp = await cb.get("/shortlists")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_get_shortlist_ok(api_client: AsyncClient) -> None:
    create_resp = await api_client.post(
        "/shortlists", json={"name": "Detail List", "description": "desc"}
    )
    shortlist_id = create_resp.json()["id"]

    response = await api_client.get(f"/shortlists/{shortlist_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == shortlist_id
    assert data["name"] == "Detail List"
    assert data["description"] == "desc"


@pytest.mark.asyncio
async def test_get_shortlist_wrong_owner_404(
    db_session_factory: async_sessionmaker,
) -> None:
    async with _make_client(db_session_factory, api_key="test-key") as ca:
        create_resp = await ca.post("/shortlists", json={"name": "Private"})
        shortlist_id = create_resp.json()["id"]

    async with _make_client(db_session_factory, api_key="other-key") as cb:
        response = await cb.get(f"/shortlists/{shortlist_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_shortlist(api_client: AsyncClient) -> None:
    create_resp = await api_client.post("/shortlists", json={"name": "To Delete"})
    shortlist_id = create_resp.json()["id"]

    delete_resp = await api_client.delete(f"/shortlists/{shortlist_id}")
    assert delete_resp.status_code == 204

    get_resp = await api_client.get(f"/shortlists/{shortlist_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_add_item_to_shortlist(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Eve")
        session.add(person)
        await session.commit()
        person_id = person.id

    create_resp = await api_client.post("/shortlists", json={"name": "Items List"})
    shortlist_id = create_resp.json()["id"]

    response = await api_client.post(
        f"/shortlists/{shortlist_id}/items",
        json={"person_id": person_id, "note": "great fit"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["person_id"] == person_id
    assert data["note"] == "great fit"
    assert data["person"]["name"] == "Eve"


@pytest.mark.asyncio
async def test_add_duplicate_item_409(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Frank")
        session.add(person)
        await session.commit()
        person_id = person.id

    create_resp = await api_client.post("/shortlists", json={"name": "Dup Test"})
    shortlist_id = create_resp.json()["id"]

    await api_client.post(f"/shortlists/{shortlist_id}/items", json={"person_id": person_id})
    response = await api_client.post(
        f"/shortlists/{shortlist_id}/items", json={"person_id": person_id}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_add_item_person_not_found_404(api_client: AsyncClient) -> None:
    create_resp = await api_client.post("/shortlists", json={"name": "No Person"})
    shortlist_id = create_resp.json()["id"]

    response = await api_client.post(
        f"/shortlists/{shortlist_id}/items",
        json={"person_id": "nonexistent-person-id"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_item(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Grace")
        session.add(person)
        await session.commit()
        person_id = person.id

    create_resp = await api_client.post("/shortlists", json={"name": "Remove Test"})
    shortlist_id = create_resp.json()["id"]

    await api_client.post(f"/shortlists/{shortlist_id}/items", json={"person_id": person_id})

    response = await api_client.delete(f"/shortlists/{shortlist_id}/items/{person_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_patch_item_note(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Hank")
        session.add(person)
        await session.commit()
        person_id = person.id

    create_resp = await api_client.post("/shortlists", json={"name": "Patch Test"})
    shortlist_id = create_resp.json()["id"]

    await api_client.post(f"/shortlists/{shortlist_id}/items", json={"person_id": person_id})

    response = await api_client.patch(
        f"/shortlists/{shortlist_id}/items/{person_id}",
        json={"note": "updated note"},
    )
    assert response.status_code == 200
    assert response.json()["note"] == "updated note"

    # Verify persistence
    get_resp = await api_client.get(f"/shortlists/{shortlist_id}")
    items = get_resp.json()["items"]
    assert any(i["note"] == "updated note" for i in items)


@pytest.mark.asyncio
async def test_patch_item_wrong_owner_returns_404(
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Ivy")
        session.add(person)
        await session.commit()
        person_id = person.id

    async with _make_client(db_session_factory, api_key="test-key") as ca:
        create_resp = await ca.post("/shortlists", json={"name": "Owner A"})
        shortlist_id = create_resp.json()["id"]
        await ca.post(f"/shortlists/{shortlist_id}/items", json={"person_id": person_id})

    async with _make_client(db_session_factory, api_key="other-key") as cb:
        response = await cb.patch(
            f"/shortlists/{shortlist_id}/items/{person_id}",
            json={"note": "hacked"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_item_not_found_404(api_client: AsyncClient) -> None:
    create_resp = await api_client.post("/shortlists", json={"name": "No Item"})
    shortlist_id = create_resp.json()["id"]

    response = await api_client.delete(f"/shortlists/{shortlist_id}/items/nonexistent-person")
    assert response.status_code == 404
