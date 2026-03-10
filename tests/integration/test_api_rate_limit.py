"""Integration test for slowapi rate limiting on GET /search."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from talent_graph.api.limiter import limiter


@pytest.fixture(autouse=False)
def reset_limiter() -> Iterator[None]:
    """Reset in-memory rate limit counters to isolate this test."""
    limiter._storage.reset()  # type: ignore[attr-defined]
    yield
    limiter._storage.reset()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_search_rate_limit_429_on_31st(
    api_client: AsyncClient,
    reset_limiter: None,
) -> None:
    """31st request to GET /search within one minute must return 429."""
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
        responses = [await api_client.get("/search?q=test") for _ in range(31)]

    for i, resp in enumerate(responses[:30]):
        assert resp.status_code == 200, f"Request {i + 1} should succeed (got {resp.status_code})"
    assert responses[30].status_code == 429, "31st request should be rate-limited (429)"
