"""TDD tests for shortlist CRUD API routes."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

# We test at the route handler level using TestClient with mocked DB sessions.


def _make_shortlist(
    shortlist_id: str = "01JTEST00000000000000000001",
    name: str = "My List",
    description: str | None = None,
) -> MagicMock:
    sl = MagicMock()
    sl.id = shortlist_id
    sl.name = name
    sl.description = description
    sl.owner_key = "default"
    sl.created_at = datetime(2025, 1, 1)
    sl.updated_at = datetime(2025, 1, 1)
    sl.items = []
    return sl


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

    def test_list_shortlists(self):
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [_make_shortlist()]
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.get("/shortlists")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_shortlist_not_found(self):
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            # get_shortlist uses execute(), not get()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.get("/shortlists/nonexistent-id")
        assert response.status_code == 404

    def test_delete_shortlist(self):
        client = self._get_client()
        sl = _make_shortlist()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=sl)
            mock_session.delete = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.delete(f"/shortlists/{sl.id}")
        assert response.status_code == 204

    def test_delete_shortlist_not_found(self):
        client = self._get_client()
        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=None)
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
            mock_session.get = AsyncMock(side_effect=[sl, mock_person])
            mock_session.add = MagicMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                f"/shortlists/{sl.id}/items",
                json={"person_id": "person_001", "note": "Strong candidate"},
            )
        assert response.status_code == 201

    def test_add_duplicate_item_rejected(self):
        """Adding the same person twice should return 409 — flush raises IntegrityError."""
        client = self._get_client()
        sl = _make_shortlist()
        mock_person = MagicMock()
        mock_person.id = "person_001"

        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(side_effect=[sl, mock_person])
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock(side_effect=IntegrityError("dup", {}, None))
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.post(
                f"/shortlists/{sl.id}/items",
                json={"person_id": "person_001"},
            )
        assert response.status_code == 409

    def test_remove_item_from_shortlist(self):
        client = self._get_client()
        sl = _make_shortlist()
        mock_item = MagicMock()

        with patch("talent_graph.api.routes.shortlist.get_db_session") as mock_ctx:
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(return_value=sl)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=mock_item)
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_session.delete = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            response = client.delete(f"/shortlists/{sl.id}/items/person_001")
        assert response.status_code == 204
