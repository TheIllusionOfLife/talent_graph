"""TDD tests for OpenAlex API client."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
import respx
from httpx import Response

from talent_graph.ingestion.openalex_client import OpenAlexClient

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def work_fixture() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((FIXTURE_DIR / "openalex_work.json").read_text()))


@pytest.fixture
def client() -> OpenAlexClient:
    return OpenAlexClient(email="test@example.com")


@respx.mock
@pytest.mark.asyncio
async def test_get_works_returns_list(client: OpenAlexClient, work_fixture: dict) -> None:
    respx.get("https://api.openalex.org/works").mock(
        return_value=Response(
            200,
            json={"results": [work_fixture], "meta": {"count": 1, "page": 1, "per_page": 25}},
        )
    )
    works = await client.get_works(query="attention mechanism", per_page=25)
    assert len(works) == 1
    assert works[0]["id"] == "https://openalex.org/W2741809807"


@respx.mock
@pytest.mark.asyncio
async def test_get_works_sends_email_polite_pool(client: OpenAlexClient) -> None:
    route = respx.get("https://api.openalex.org/works").mock(
        return_value=Response(200, json={"results": [], "meta": {"count": 0}})
    )
    await client.get_works(query="test")
    url = str(route.calls[0].request.url)
    assert "mailto=" in url and "example.com" in url


@respx.mock
@pytest.mark.asyncio
async def test_get_works_paginates(client: OpenAlexClient, work_fixture: dict) -> None:
    """Should follow cursor pagination until no next_cursor."""
    respx.get("https://api.openalex.org/works").mock(
        side_effect=[
            Response(
                200,
                json={
                    "results": [work_fixture],
                    "meta": {"count": 2, "next_cursor": "cursor-abc"},
                },
            ),
            Response(
                200,
                json={
                    "results": [work_fixture],
                    "meta": {"count": 2, "next_cursor": None},
                },
            ),
        ]
    )
    works = await client.get_works_paginated(query="test", max_results=100)
    assert len(works) == 2


@respx.mock
@pytest.mark.asyncio
async def test_get_works_retries_on_503(client: OpenAlexClient, work_fixture: dict) -> None:
    respx.get("https://api.openalex.org/works").mock(
        side_effect=[
            Response(503, text="Service Unavailable"),
            Response(200, json={"results": [work_fixture], "meta": {"count": 1}}),
        ]
    )
    works = await client.get_works(query="test")
    assert len(works) == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_author_returns_dict(client: OpenAlexClient) -> None:
    author_id = "A5023888391"
    respx.get(f"https://api.openalex.org/authors/{author_id}").mock(
        return_value=Response(
            200,
            json={
                "id": f"https://openalex.org/{author_id}",
                "display_name": "Ashish Vaswani",
                "orcid": None,
                "last_known_institution": None,
            },
        )
    )
    author = await client.get_author(author_id)
    assert author["display_name"] == "Ashish Vaswani"
