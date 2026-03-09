"""TDD tests for deterministic entity resolution."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from talent_graph.entity_resolution.deterministic import resolve_deterministic
from talent_graph.normalize.common_schema import PersonRecord


def _make_session(scalar_result: str | None) -> AsyncMock:
    """Return a mock AsyncSession that returns scalar_result from execute().

    Handles both scalar_one_or_none() (used by most lookups) and
    scalars().first() (used by the email lookup to avoid MultipleResultsFound).
    """
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scalar_result
    mock_result.scalars.return_value.first.return_value = scalar_result
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_resolves_by_openalex_author_id() -> None:
    session = _make_session("person_existing_openalex")
    person = PersonRecord(name="Alice", openalex_author_id="A5023888391")
    result = await resolve_deterministic(session, person)
    assert result == "person_existing_openalex"


@pytest.mark.asyncio
async def test_openalex_author_id_takes_priority_over_orcid() -> None:
    """openalex_author_id is checked first and stops further queries on match."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "person_openalex_match"
    session.execute.return_value = mock_result

    person = PersonRecord(
        name="Alice",
        openalex_author_id="A5023888391",
        orcid="0000-0001-2345-6789",
    )
    result = await resolve_deterministic(session, person)
    assert result == "person_openalex_match"
    assert session.execute.call_count == 1  # stopped after openalex_author_id


@pytest.mark.asyncio
async def test_resolves_by_orcid() -> None:
    session = _make_session("person_existing_123")
    person = PersonRecord(name="Alice", orcid="https://orcid.org/0000-0001-2345-6789")
    result = await resolve_deterministic(session, person)
    assert result == "person_existing_123"


@pytest.mark.asyncio
async def test_normalizes_orcid_url_to_bare_id() -> None:
    """ORCID 'https://orcid.org/0000-XXXX-XXXX-XXXX' → '0000-XXXX-XXXX-XXXX'."""
    session = _make_session(None)
    person = PersonRecord(name="Alice", orcid="https://orcid.org/0000-0001-2345-6789")
    await resolve_deterministic(session, person)
    # The ORCID query must use the bare ID, not the full URL
    call_args = session.execute.call_args_list
    assert call_args, "Expected at least one DB query"
    first_stmt = call_args[0][0][0]
    param_values = list(first_stmt.compile().params.values())
    assert "0000-0001-2345-6789" in param_values, f"Bare ORCID not found in params: {param_values}"
    assert not any("orcid.org" in str(v) for v in param_values), "Full ORCID URL leaked into query"


@pytest.mark.asyncio
async def test_resolves_by_github_login() -> None:
    session = _make_session("person_existing_456")
    person = PersonRecord(name="Bob", github_login="bobdev")
    result = await resolve_deterministic(session, person)
    assert result == "person_existing_456"


@pytest.mark.asyncio
async def test_resolves_github_login_from_openalex_homepage() -> None:
    """Extract github_login from OpenAlex homepage URL."""
    session = _make_session("person_existing_789")
    person = PersonRecord(name="Carol", homepage="https://github.com/caroldev")
    result = await resolve_deterministic(session, person)
    assert result == "person_existing_789"


@pytest.mark.asyncio
async def test_resolves_by_email() -> None:
    session = _make_session("person_existing_abc")
    person = PersonRecord(name="Dave", email="dave@example.com")
    result = await resolve_deterministic(session, person)
    assert result == "person_existing_abc"


@pytest.mark.asyncio
async def test_returns_none_when_no_match() -> None:
    session = _make_session(None)
    person = PersonRecord(name="Unknown", openalex_author_id="A999")
    result = await resolve_deterministic(session, person)
    assert result is None


@pytest.mark.asyncio
async def test_skips_query_when_no_identifiers() -> None:
    """No external IDs → no DB queries, returns None immediately."""
    session = _make_session(None)
    person = PersonRecord(name="No IDs")
    result = await resolve_deterministic(session, person)
    assert result is None
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_orcid_takes_priority_over_github() -> None:
    """Deterministic: ORCID match found → return immediately, skip github check."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = "person_orcid_match"
    session.execute.return_value = mock_result

    person = PersonRecord(
        name="Alice",
        orcid="0000-0001-2345-6789",
        github_login="alice-dev",
    )
    result = await resolve_deterministic(session, person)
    assert result == "person_orcid_match"
    # Should have stopped after the first (ORCID) query
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_non_github_homepage_ignored() -> None:
    """Homepage that is not a GitHub URL should not be used for matching."""
    session = _make_session(None)
    person = PersonRecord(name="Eve", homepage="https://eve.dev")
    result = await resolve_deterministic(session, person)
    assert result is None
    session.execute.assert_not_called()
