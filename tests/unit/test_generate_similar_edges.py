"""Tests for SIMILAR_TO edge generation — cosine similarity, top-K filtering."""

import numpy as np
import pytest


class TestCosineSimilarityPairs:
    """Test the _compute_similar_pairs helper."""

    def _compute(
        self,
        person_ids: list[str],
        embeddings: list[list[float]],
        threshold: float = 0.7,
        top_k: int = 5,
    ) -> list[dict[str, object]]:
        from talent_graph.scripts.generate_similar_edges import _compute_similar_pairs

        vecs = np.array(embeddings, dtype=np.float32)
        return _compute_similar_pairs(person_ids, vecs, threshold=threshold, top_k=top_k)

    def test_identical_vectors_similarity_one(self) -> None:
        """Identical normalized vectors have similarity ~1.0."""
        vec = [1.0, 0.0, 0.0]
        pairs = self._compute(["a", "b"], [vec, vec], threshold=0.9)
        assert len(pairs) == 1
        assert pairs[0]["person_id_a"] in ("a", "b")
        assert pairs[0]["person_id_b"] in ("a", "b")
        assert pairs[0]["person_id_a"] != pairs[0]["person_id_b"]
        assert float(str(pairs[0]["similarity"])) > 0.9

    def test_orthogonal_vectors_excluded(self) -> None:
        """Orthogonal vectors have similarity 0, below any reasonable threshold."""
        pairs = self._compute(
            ["a", "b"],
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
            threshold=0.5,
        )
        assert len(pairs) == 0

    def test_self_pair_excluded(self) -> None:
        """A person is never paired with themselves."""
        vec = [1.0, 0.0]
        pairs = self._compute(["a"], [vec], threshold=0.0)
        assert len(pairs) == 0

    def test_top_k_limits_results(self) -> None:
        """Each person gets at most top_k partners."""
        # 4 identical vectors → each could pair with 3 others
        vec = [1.0, 0.0]
        pairs = self._compute(["a", "b", "c", "d"], [vec] * 4, threshold=0.5, top_k=1)
        # With top_k=1 per person, max 4 pairs (one per person), but deduped
        assert len(pairs) <= 4

    def test_canonical_ordering(self) -> None:
        """Output pairs have person_id_a < person_id_b (sorted)."""
        vec = [1.0, 0.0]
        pairs = self._compute(["z", "a"], [vec, vec], threshold=0.5)
        for pair in pairs:
            assert str(pair["person_id_a"]) < str(pair["person_id_b"])
