"""Tests for LIKELY_EXPERT_IN edge generation — concept frequency, threshold filtering."""


class TestConceptFrequencyCounting:
    """Test the _count_person_concepts helper."""

    def _count(
        self,
        person_papers: list[dict[str, str]],
        min_papers: int = 3,
    ) -> list[dict[str, object]]:
        from talent_graph.scripts.generate_expert_edges import _count_person_concepts

        return _count_person_concepts(person_papers, min_papers=min_papers)  # type: ignore[arg-type]

    def test_person_with_enough_papers_on_concept(self) -> None:
        """Person with 3+ papers on a concept gets an edge."""
        data = [
            {"person_id": "p1", "concept_id": "c1"},
            {"person_id": "p1", "concept_id": "c1"},
            {"person_id": "p1", "concept_id": "c1"},
        ]
        edges = self._count(data, min_papers=3)
        assert len(edges) == 1
        assert edges[0]["person_id"] == "p1"
        assert edges[0]["concept_id"] == "c1"
        assert edges[0]["paper_count"] == 3

    def test_person_below_threshold_excluded(self) -> None:
        """Person with <3 papers on a concept does not get an edge."""
        data = [
            {"person_id": "p1", "concept_id": "c1"},
            {"person_id": "p1", "concept_id": "c1"},
        ]
        edges = self._count(data, min_papers=3)
        assert len(edges) == 0

    def test_multiple_persons_and_concepts(self) -> None:
        """Multiple persons × concepts computed correctly."""
        data = [
            {"person_id": "p1", "concept_id": "c1"},
            {"person_id": "p1", "concept_id": "c1"},
            {"person_id": "p1", "concept_id": "c1"},
            {"person_id": "p1", "concept_id": "c2"},
            {"person_id": "p2", "concept_id": "c1"},
            {"person_id": "p2", "concept_id": "c1"},
            {"person_id": "p2", "concept_id": "c1"},
            {"person_id": "p2", "concept_id": "c1"},
        ]
        edges = self._count(data, min_papers=3)
        assert len(edges) == 2
        edge_keys = {(e["person_id"], e["concept_id"]) for e in edges}
        assert ("p1", "c1") in edge_keys
        assert ("p2", "c1") in edge_keys

    def test_empty_input(self) -> None:
        edges = self._count([], min_papers=3)
        assert edges == []
