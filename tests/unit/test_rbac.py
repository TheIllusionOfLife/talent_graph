"""Tests for RBAC: admin routes require exact key, user routes accept any non-empty key."""

import pytest

from talent_graph.api.auth import require_admin_key, require_any_api_key, require_user_key

ADMIN_KEY = "test-admin-key"
RANDOM_USER_KEY = "some-random-user-key"


@pytest.fixture(autouse=True)
def _patch_settings():
    """Patch settings so API_KEY = ADMIN_KEY."""
    from unittest.mock import patch

    from talent_graph.config.settings import Settings

    settings = Settings(
        database_url="postgresql+asyncpg://x:x@localhost/x",
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="test",
        api_key=ADMIN_KEY,
        app_secret="test-secret",
    )
    with patch("talent_graph.api.auth.get_settings", return_value=settings):
        yield


@pytest.mark.asyncio
class TestRBAC:
    """Test auth functions directly — no need for full app or DB."""

    async def test_admin_key_rejects_random_key(self) -> None:
        """require_admin_key rejects a non-admin key with 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_key(RANDOM_USER_KEY)
        assert exc_info.value.status_code == 401

    async def test_admin_key_accepts_admin_key(self) -> None:
        """require_admin_key accepts the configured admin key."""
        result = await require_admin_key(ADMIN_KEY)
        assert result == ADMIN_KEY

    async def test_user_key_accepts_random_key(self) -> None:
        """require_user_key accepts any non-empty key."""
        result = await require_user_key(RANDOM_USER_KEY)
        assert result == RANDOM_USER_KEY

    async def test_user_key_accepts_admin_key(self) -> None:
        """require_user_key also accepts the admin key (backward compatible)."""
        result = await require_user_key(ADMIN_KEY)
        assert result == ADMIN_KEY

    async def test_user_key_rejects_empty_key(self) -> None:
        """require_user_key rejects empty key with 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_user_key("")
        assert exc_info.value.status_code == 401

    async def test_user_key_rejects_none(self) -> None:
        """require_user_key rejects None (no header) with 401."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_user_key(None)
        assert exc_info.value.status_code == 401

    async def test_require_user_key_is_require_any_api_key(self) -> None:
        """require_user_key is the same function as require_any_api_key."""
        assert require_user_key is require_any_api_key
