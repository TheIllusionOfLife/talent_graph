"""Integration tests for GET /person/{id} and POST /person/{id}/brief."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.factories import OrgFactory, PersonFactory


@pytest.mark.asyncio
async def test_get_person_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/person/nonexistent", headers={"X-API-Key": "bad"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_person_404(api_client: AsyncClient) -> None:
    response = await api_client.get("/person/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_person_ok(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        org = OrgFactory.build(name="MIT", country_code="US", type="education")
        person = PersonFactory.build(name="Alice", org_id=org.id)
        session.add_all([org, person])
        await session.commit()
        person_id = person.id

    response = await api_client.get(f"/person/{person_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == person_id
    assert data["name"] == "Alice"
    assert data["papers"] == []
    assert data["repos"] == []
    assert data["org"]["name"] == "MIT"


@pytest.mark.asyncio
async def test_get_person_no_org(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Bob")
        session.add(person)
        await session.commit()
        person_id = person.id

    response = await api_client.get(f"/person/{person_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["org"] is None


@pytest.mark.asyncio
async def test_get_person_brief_404(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/person/does-not-exist/brief",
        json={"seed_text": "machine learning research"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_person_brief_ok(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Carol")
        session.add(person)
        await session.commit()
        person_id = person.id

    with patch(
        "talent_graph.api.routes.person.explain_with_meta",
        new_callable=AsyncMock,
        return_value=("Carol is an expert in ML.", False),
    ):
        response = await api_client.post(
            f"/person/{person_id}/brief",
            json={"seed_text": "machine learning"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["person_id"] == person_id
    assert data["explanation"] == "Carol is an expert in ML."
    assert data["fallback"] is False


@pytest.mark.asyncio
async def test_get_person_brief_fallback(
    api_client: AsyncClient,
    db_session_factory: async_sessionmaker,
) -> None:
    async with db_session_factory() as session:
        person = PersonFactory.build(name="Dave")
        session.add(person)
        await session.commit()
        person_id = person.id

    with patch(
        "talent_graph.api.routes.person.explain_with_meta",
        new_callable=AsyncMock,
        return_value=("Fallback explanation for Dave.", True),
    ):
        response = await api_client.post(
            f"/person/{person_id}/brief",
            json={"seed_text": "deep learning"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["fallback"] is True
    assert "Fallback" in data["explanation"]
