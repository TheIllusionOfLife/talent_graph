"""Integration tests for saved search CRUD routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

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
async def test_create_saved_search(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/searches", json={"name": "ML Search", "query": "machine learning"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "ML Search"
    assert data["query"] == "machine learning"
    assert "id" in data
    assert data["filters"] is None
    assert data["last_run_at"] is None


@pytest.mark.asyncio
async def test_create_saved_search_with_filters(api_client: AsyncClient) -> None:
    filters = {"mode": "standard", "limit": 20}
    response = await api_client.post(
        "/searches",
        json={"name": "Filtered", "query": "deep learning", "filters": filters},
    )
    assert response.status_code == 201
    assert response.json()["filters"] == filters


@pytest.mark.asyncio
async def test_list_saved_searches(api_client: AsyncClient) -> None:
    await api_client.post("/searches", json={"name": "Search A", "query": "NLP"})
    await api_client.post("/searches", json={"name": "Search B", "query": "CV"})

    response = await api_client.get("/searches")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    names = {item["name"] for item in data}
    assert names == {"Search A", "Search B"}


@pytest.mark.asyncio
async def test_list_saved_searches_own_only(
    db_session_factory: async_sessionmaker,
) -> None:
    """Key A creates a saved search; key B sees an empty list."""
    async with _make_client(db_session_factory, api_key="user-a") as ca:
        resp = await ca.post("/searches", json={"name": "Private", "query": "secret"})
        assert resp.status_code == 201

    async with _make_client(db_session_factory, api_key="user-b") as cb:
        resp = await cb.get("/searches")
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_get_saved_search_ok(api_client: AsyncClient) -> None:
    create_resp = await api_client.post(
        "/searches", json={"name": "Detail", "query": "transformers"}
    )
    search_id = create_resp.json()["id"]

    response = await api_client.get(f"/searches/{search_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == search_id
    assert data["query"] == "transformers"


@pytest.mark.asyncio
async def test_get_saved_search_wrong_owner_404(
    db_session_factory: async_sessionmaker,
) -> None:
    async with _make_client(db_session_factory, api_key="owner-a") as ca:
        create_resp = await ca.post("/searches", json={"name": "A search", "query": "q"})
        search_id = create_resp.json()["id"]

    async with _make_client(db_session_factory, api_key="owner-b") as cb:
        response = await cb.get(f"/searches/{search_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_saved_search(api_client: AsyncClient) -> None:
    create_resp = await api_client.post(
        "/searches", json={"name": "To Delete", "query": "bye"}
    )
    search_id = create_resp.json()["id"]

    delete_resp = await api_client.delete(f"/searches/{search_id}")
    assert delete_resp.status_code == 204

    get_resp = await api_client.get(f"/searches/{search_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_saved_search_wrong_owner_404(
    db_session_factory: async_sessionmaker,
) -> None:
    async with _make_client(db_session_factory, api_key="owner-a") as ca:
        create_resp = await ca.post("/searches", json={"name": "Mine", "query": "q"})
        search_id = create_resp.json()["id"]

    async with _make_client(db_session_factory, api_key="owner-b") as cb:
        response = await cb.delete(f"/searches/{search_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_saved_search_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/searches",
        json={"name": "Test", "query": "q"},
        headers={"X-API-Key": ""},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_saved_search_invalid_body_422(api_client: AsyncClient) -> None:
    response = await api_client.post("/searches", json={"name": "No query"})
    assert response.status_code == 422
