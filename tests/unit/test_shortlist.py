"""TDD tests for shortlist CRUD API routes."""

import hashlib
import hmac
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg.exceptions
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

# Default test secret matches get_settings().app_secret in the test environment
_TEST_SECRET = "change-me-in-production"


def _owner_hash_test(api_key: str) -> str:
    return hmac.new(_TEST_SECRET.encode(), api_key.encode(), hashlib.sha256).hexdigest()


def _make_shortlist(
    shortlist_id: str = "01JTEST00000000000000000001",
    name: str = "My List",
    description: str | None = None,
    owner_key: str = "test-key",
) -> MagicMock:
    sl = MagicMock()
    sl.id = shortlist_id
    sl.name = name
    sl.description = description
    # Store the HMAC hash as production code does, not the raw key
    sl.owner_key = _owner_hash_test(owner_key)
    sl.created_at = datetime(2025, 1, 1)
    sl.updated_at = datetime(2025, 1, 1)
    sl.items = []
    return sl


def _execute_returning(value: object) -> AsyncMock:
    """Return an async execute mock whose scalar_one_or_none() returns value."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=value)
    return AsyncMock(return_value=mock_result)


class TestShortlistCRUD:
    """Shortlist API route unit tests using mocked DB."""

    def _get_client(self) -> TestClient:
        from talent_graph.api.main import create_app

        app = create_app()
        return TestClient(app, headers={"X-API-Key": "test-key"})

    def test_create_shortlist(self):
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                "/shortlists",
                json={"name": "AI Researchers", "description": "Top picks"},
            )
        assert response.status_code == 201
        data = response.json()
        # owner_key is not exposed in the response (stored as a hash internally)
        assert "owner_key" not in data

    def test_create_shortlist_sets_owner_key_from_header(self):
        """owner_key must be HMAC of the API key, never raw or 'default'."""
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post("/shortlists", json={"name": "Test"})
        assert response.status_code == 201
        # Verify that the session.add was called with a Shortlist whose owner_key
        # is the HMAC-SHA256 of "test-key" (not the raw key, not "default")
        added = mock_session.add.call_args[0][0]
        assert added.owner_key == _owner_hash_test("test-key")

    def test_create_shortlist_requires_auth(self):
        from talent_graph.api.main import create_app

        app = create_app()
        client = TestClient(app)  # no API key header
        response = client.post("/shortlists", json={"name": "No Auth"})
        assert response.status_code == 401

    def test_get_shortlist_cross_key_returns_404(self):
        """owner_key filter: DB returns no row when hash doesn't match → 404."""
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            # Simulate owner_key mismatch — WHERE clause filters out the row
            mock_session.execute = _execute_returning(None)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.get("/shortlists/some-id")
        assert response.status_code == 404

    def test_list_shortlists(self):
        client = self._get_client()
        sl = _make_shortlist()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            # list_shortlists uses result.all() returning (shortlist, count) tuples
            mock_result.all = MagicMock(return_value=[(sl, 2)])
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.get("/shortlists")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["item_count"] == 2

    def test_get_shortlist_not_found(self):
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.execute = _execute_returning(None)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.get("/shortlists/nonexistent-id")
        assert response.status_code == 404

    def test_get_shortlist_found(self):
        client = self._get_client()
        sl = _make_shortlist()
        sl.items = []
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.execute = _execute_returning(sl)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.get(f"/shortlists/{sl.id}")
        assert response.status_code == 200
        assert response.json()["id"] == sl.id

    def test_delete_shortlist(self):
        client = self._get_client()
        sl = _make_shortlist()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            # delete_shortlist uses execute() → scalar_one_or_none()
            mock_session.execute = _execute_returning(sl)
            mock_session.delete = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.delete(f"/shortlists/{sl.id}")
        assert response.status_code == 204

    def test_delete_shortlist_not_found(self):
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.execute = _execute_returning(None)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.delete("/shortlists/nonexistent-id")
        assert response.status_code == 404

    def test_add_item_to_shortlist(self):
        client = self._get_client()
        sl = _make_shortlist()

        mock_person = MagicMock()
        mock_person.id = "person_001"
        mock_person.name = "Alice"
        mock_person.openalex_author_id = None
        mock_person.github_login = None

        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            # add_item uses execute() for shortlist, get() for person
            mock_session.execute = _execute_returning(sl)
            mock_session.get = AsyncMock(return_value=mock_person)
            mock_session.add = MagicMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                f"/shortlists/{sl.id}/items",
                json={"person_id": "person_001", "note": "Strong candidate"},
            )
        assert response.status_code == 201

    def test_add_duplicate_item_rejected(self):
        """Adding the same person twice should return 409."""
        client = self._get_client()
        sl = _make_shortlist()
        mock_person = MagicMock()
        mock_person.id = "person_001"

        # Build an IntegrityError whose orig is a real asyncpg UniqueViolationError
        orig = asyncpg.exceptions.UniqueViolationError()
        ie = IntegrityError("dup", {}, orig)
        ie.orig = orig

        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.execute = _execute_returning(sl)
            mock_session.get = AsyncMock(return_value=mock_person)
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock(side_effect=ie)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                f"/shortlists/{sl.id}/items",
                json={"person_id": "person_001"},
            )
        assert response.status_code == 409

    def test_add_item_non_unique_integrity_error_reraises(self):
        """Non-unique IntegrityError (e.g. FK violation) must not be swallowed as 409."""
        client = self._get_client()
        sl = _make_shortlist()
        mock_person = MagicMock()
        mock_person.id = "person_001"

        # IntegrityError without a UniqueViolationError orig — should propagate
        ie = IntegrityError("fk", {}, Exception("other"))
        ie.orig = Exception("other constraint")

        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.execute = _execute_returning(sl)
            mock_session.get = AsyncMock(return_value=mock_person)
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock(side_effect=ie)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(IntegrityError):
                client.post(
                    f"/shortlists/{sl.id}/items",
                    json={"person_id": "person_001"},
                )

    def test_remove_item_from_shortlist(self):
        client = self._get_client()
        sl = _make_shortlist()
        mock_item = MagicMock()

        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            # remove_item calls execute() twice: once for shortlist, once for item
            sl_result = MagicMock()
            sl_result.scalar_one_or_none = MagicMock(return_value=sl)
            item_result = MagicMock()
            item_result.scalar_one_or_none = MagicMock(return_value=mock_item)
            mock_session.execute = AsyncMock(side_effect=[sl_result, item_result])
            mock_session.delete = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.delete(f"/shortlists/{sl.id}/items/person_001")
        assert response.status_code == 204
