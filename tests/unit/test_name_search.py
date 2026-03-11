"""Tests for text-based name search fallback."""

from talent_graph.storage.vector_store import _build_name_query


class TestBuildNameQuery:
    """Test the name search SQL query builder."""

    def test_returns_select_statement(self) -> None:
        """Should return a valid SQLAlchemy select statement."""
        stmt = _build_name_query("Daniel", limit=10)
        # Should compile without error
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "persons" in compiled.lower()

    def test_limit_applied(self) -> None:
        """Limit clause should be in the compiled query."""
        stmt = _build_name_query("test", limit=5)
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        # SQLAlchemy adds LIMIT
        assert "LIMIT" in compiled.upper() or ":param" in compiled
