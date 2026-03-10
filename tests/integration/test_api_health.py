"""Integration tests for GET /health."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(api_client: AsyncClient) -> None:
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "postgres" in data
    assert "neo4j" in data


@pytest.mark.asyncio
async def test_health_no_auth_required(api_client: AsyncClient) -> None:
    """Health endpoint must be reachable without an API key."""
    response = await api_client.get("/health", headers={})
    # May be 200 (ok) or 503 (degraded) depending on mock state, never 401
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
