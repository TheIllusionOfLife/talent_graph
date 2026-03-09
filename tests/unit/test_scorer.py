"""TDD tests for ranking/scorer.py and ranking/modes.py."""

import pytest

from talent_graph.features.person_features import PersonFeatures
from talent_graph.ranking.modes import RankMode
from talent_graph.ranking.scorer import score_candidate, WEIGHTS


class TestRankMode:
    def test_enum_values(self):
        assert RankMode.STANDARD.value == "standard"
        assert RankMode.HIDDEN.value == "hidden"
        assert RankMode.EMERGING.value == "emerging"

    def test_all_modes_present(self):
        modes = {m.value for m in RankMode}
        assert modes == {"standard", "hidden", "emerging"}


class TestWeights:
    def test_all_modes_defined(self):
        for mode in RankMode:
            assert mode in WEIGHTS

    def test_weights_sum_to_one(self):
        for mode, w in WEIGHTS.items():
            total = sum(w.values())
            assert total == pytest.approx(1.0), f"{mode} weights sum to {total}"

    def test_required_keys_present(self):
        required = {
            "semantic_similarity", "graph_proximity", "novelty",
            "growth", "evidence_quality", "credibility"
        }
        for mode, w in WEIGHTS.items():
            assert set(w.keys()) == required, f"missing keys in {mode}"

    def test_standard_weights_match_spec(self):
        w = WEIGHTS[RankMode.STANDARD]
        assert w["semantic_similarity"] == pytest.approx(0.30)
        assert w["graph_proximity"] == pytest.approx(0.20)
        assert w["novelty"] == pytest.approx(0.15)
        assert w["growth"] == pytest.approx(0.15)
        assert w["evidence_quality"] == pytest.approx(0.10)
        assert w["credibility"] == pytest.approx(0.10)

    def test_hidden_weights_match_spec(self):
        w = WEIGHTS[RankMode.HIDDEN]
        assert w["semantic_similarity"] == pytest.approx(0.20)
        assert w["graph_proximity"] == pytest.approx(0.10)
        assert w["novelty"] == pytest.approx(0.25)
        assert w["growth"] == pytest.approx(0.10)
        assert w["evidence_quality"] == pytest.approx(0.20)
        assert w["credibility"] == pytest.approx(0.15)

    def test_emerging_weights_match_spec(self):
        w = WEIGHTS[RankMode.EMERGING]
        assert w["semantic_similarity"] == pytest.approx(0.25)
        assert w["graph_proximity"] == pytest.approx(0.15)
        assert w["novelty"] == pytest.approx(0.10)
        assert w["growth"] == pytest.approx(0.30)
        assert w["evidence_quality"] == pytest.approx(0.10)
        assert w["credibility"] == pytest.approx(0.10)


class TestScoreCandidate:
    def _features(self, **kwargs) -> PersonFeatures:
        defaults = dict(
            semantic_similarity=0.5,
            graph_proximity=0.5,
            novelty=0.5,
            growth=0.5,
            evidence_quality=0.5,
            credibility=0.5,
        )
        defaults.update(kwargs)
        return PersonFeatures(**defaults)

    def test_uniform_features_returns_dot5(self):
        features = self._features()
        score = score_candidate(features, RankMode.STANDARD)
        assert score == pytest.approx(0.5)

    def test_all_ones_returns_one(self):
        features = self._features(
            semantic_similarity=1.0,
            graph_proximity=1.0,
            novelty=1.0,
            growth=1.0,
            evidence_quality=1.0,
            credibility=1.0,
        )
        assert score_candidate(features, RankMode.STANDARD) == pytest.approx(1.0)

    def test_all_zeros_returns_zero(self):
        features = self._features(
            semantic_similarity=0.0,
            graph_proximity=0.0,
            novelty=0.0,
            growth=0.0,
            evidence_quality=0.0,
            credibility=0.0,
        )
        assert score_candidate(features, RankMode.STANDARD) == pytest.approx(0.0)

    def test_score_in_range(self):
        for mode in RankMode:
            score = score_candidate(self._features(), mode)
            assert 0.0 <= score <= 1.0, f"out of range for {mode}"

    def test_hidden_mode_amplifies_novelty(self):
        """A person with high novelty should score higher in HIDDEN vs STANDARD."""
        features = self._features(novelty=1.0, growth=0.0, semantic_similarity=0.0,
                                   graph_proximity=0.0, evidence_quality=0.0, credibility=0.0)
        standard = score_candidate(features, RankMode.STANDARD)
        hidden = score_candidate(features, RankMode.HIDDEN)
        assert hidden > standard

    def test_emerging_mode_amplifies_growth(self):
        """A person with high growth should score higher in EMERGING vs STANDARD."""
        features = self._features(growth=1.0, novelty=0.0, semantic_similarity=0.0,
                                   graph_proximity=0.0, evidence_quality=0.0, credibility=0.0)
        standard = score_candidate(features, RankMode.STANDARD)
        emerging = score_candidate(features, RankMode.EMERGING)
        assert emerging > standard

    def test_score_is_float(self):
        result = score_candidate(self._features(), RankMode.STANDARD)
        assert isinstance(result, float)
