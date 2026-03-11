"""Tests for blended vector + name search."""

from talent_graph.api.routes.search import _blend_results
from talent_graph.storage.vector_store import _build_name_query


class TestBuildNameQuery:
    """Test the name search SQL query builder."""

    def test_returns_select_with_persons_table(self) -> None:
        stmt = _build_name_query("Daniel", limit=10)
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "persons" in compiled.lower()

    def test_limit_applied(self) -> None:
        stmt = _build_name_query("test", limit=5)
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        assert "LIMIT" in compiled.upper() or ":param" in compiled

    def test_ilike_pattern(self) -> None:
        stmt = _build_name_query("Kipp", limit=10)
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
        # SQLAlchemy compiles ILIKE as lower(...) LIKE lower(...)
        assert "like" in compiled.lower()


class TestBlendResults:
    """Test the result blending logic extracted from the search route."""

    def test_name_match_appears_when_vector_misses(self) -> None:
        """Name matches should appear even when vector search returns unrelated results."""
        vec_rows = [
            {"id": "a1", "name": "Alice", "distance": 0.4},
            {"id": "a2", "name": "Bob", "distance": 0.5},
        ]
        name_rows = [
            {"id": "a3", "name": "Michael Kipp", "distance": 0.5},
        ]
        blended = _blend_results(vec_rows, name_rows, query="Michael Kipp", limit=20)
        ids = [r["id"] for r in blended]
        assert "a3" in ids

    def test_exact_name_match_ranked_above_weak_vector(self) -> None:
        """Exact name matches should rank higher than weak vector results."""
        vec_rows = [
            {"id": "a1", "name": "Alice", "distance": 0.6},
        ]
        name_rows = [
            {"id": "a2", "name": "Michael Kipp", "distance": 0.5},
        ]
        blended = _blend_results(vec_rows, name_rows, query="Michael Kipp", limit=20)
        assert blended[0]["id"] == "a2"

    def test_deduplication_keeps_better_score(self) -> None:
        """When a person appears in both and name is exact match, boost wins."""
        vec_rows = [
            {"id": "a1", "name": "Michael Kipp", "distance": 0.3},
        ]
        name_rows = [
            {"id": "a1", "name": "Michael Kipp", "distance": 0.5},
        ]
        blended = _blend_results(vec_rows, name_rows, query="Michael Kipp", limit=20)
        assert len(blended) == 1
        assert blended[0]["distance"] == 0.1  # exact name match boost wins

    def test_partial_name_match_keeps_original_distance(self) -> None:
        """Partial name matches should NOT get the boost — keep original distance."""
        vec_rows: list[dict] = []
        name_rows = [
            {"id": "a1", "name": "Johnson Smith", "distance": 0.5},
        ]
        blended = _blend_results(vec_rows, name_rows, query="John", limit=20)
        assert len(blended) == 1
        assert blended[0]["distance"] == 0.5  # no boost for partial match

    def test_limit_respected(self) -> None:
        vec_rows = [{"id": f"v{i}", "name": f"Vec{i}", "distance": 0.3} for i in range(10)]
        name_rows = [{"id": f"n{i}", "name": f"Name{i}", "distance": 0.5} for i in range(10)]
        blended = _blend_results(vec_rows, name_rows, query="irrelevant", limit=5)
        assert len(blended) == 5

    def test_empty_name_results(self) -> None:
        """When name search returns nothing, vector results are returned as-is."""
        vec_rows = [
            {"id": "a1", "name": "Alice", "distance": 0.4},
        ]
        blended = _blend_results(vec_rows, [], query="Alice", limit=20)
        assert len(blended) == 1
        assert blended[0]["id"] == "a1"

    def test_empty_vector_results(self) -> None:
        """When vector search returns nothing, name results are returned."""
        name_rows = [
            {"id": "a1", "name": "Michael Kipp", "distance": 0.5},
        ]
        blended = _blend_results([], name_rows, query="Michael Kipp", limit=20)
        assert len(blended) == 1
        assert blended[0]["id"] == "a1"
        assert blended[0]["distance"] == 0.1  # exact match gets boost
