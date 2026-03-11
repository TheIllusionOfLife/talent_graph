"""Unit tests for lookalike discovery: self-exclusion, similarity calc."""

import pytest

from talent_graph.api.routes.lookalike import _build_results


class TestBuildResults:
    """Verify result transformation from vector store rows."""

    def test_basic_transform(self) -> None:
        rows = [
            {"id": "p1", "name": "Alice", "distance": 0.1},
            {"id": "p2", "name": "Bob", "distance": 0.3},
        ]
        results = _build_results(rows, exclude_id="p_other")
        assert len(results) == 2
        assert results[0].id == "p1"
        assert results[0].similarity == pytest.approx(0.9)
        assert results[1].similarity == pytest.approx(0.7)

    def test_self_exclusion(self) -> None:
        rows = [
            {"id": "p_self", "name": "Self", "distance": 0.0},
            {"id": "p2", "name": "Bob", "distance": 0.2},
        ]
        results = _build_results(rows, exclude_id="p_self")
        assert len(results) == 1
        assert results[0].id == "p2"

    def test_empty_rows(self) -> None:
        results = _build_results([], exclude_id="p1")
        assert results == []

    def test_similarity_clamp(self) -> None:
        """Distance > 1 should clamp similarity to 0."""
        rows = [{"id": "p1", "name": "Far", "distance": 1.5}]
        results = _build_results(rows, exclude_id="other")
        assert results[0].similarity == 0.0
