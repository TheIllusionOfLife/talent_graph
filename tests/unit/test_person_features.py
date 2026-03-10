"""TDD tests for features/person_features.py."""

import pytest

from talent_graph.features.person_features import (
    PersonFeatures,
    compute_credibility,
    compute_evidence_quality,
    compute_growth,
    compute_novelty,
)


class TestComputeNovelty:
    """Novelty = inverse of citation prominence; uncited hidden experts score high."""

    def test_zero_citations_max_novelty(self):
        score = compute_novelty(citation_count=0, paper_count=0)
        assert score == pytest.approx(1.0)

    def test_high_citations_low_novelty(self):
        score = compute_novelty(citation_count=10000, paper_count=50)
        assert score < 0.3

    def test_moderate_citations_moderate_novelty(self):
        score = compute_novelty(citation_count=100, paper_count=5)
        assert 0.2 <= score <= 0.9

    def test_score_in_range(self):
        for citations in [0, 1, 10, 100, 1000, 50000]:
            score = compute_novelty(citation_count=citations, paper_count=5)
            assert 0.0 <= score <= 1.0, f"out of range for citations={citations}"

    def test_more_citations_lower_novelty(self):
        low = compute_novelty(citation_count=10, paper_count=5)
        high = compute_novelty(citation_count=1000, paper_count=5)
        assert low > high


class TestComputeGrowth:
    """Growth = recent paper velocity signal."""

    def test_no_papers_zero_growth(self):
        score = compute_growth(recent_paper_count=0, total_paper_count=0, years_active=0)
        assert score == pytest.approx(0.0)

    def test_high_recent_activity(self):
        score = compute_growth(recent_paper_count=10, total_paper_count=12, years_active=3)
        assert score > 0.7

    def test_score_in_range(self):
        for recent in [0, 1, 5, 20]:
            score = compute_growth(recent_paper_count=recent, total_paper_count=50, years_active=5)
            assert 0.0 <= score <= 1.0

    def test_more_recent_higher_growth(self):
        low = compute_growth(recent_paper_count=1, total_paper_count=20, years_active=5)
        high = compute_growth(recent_paper_count=15, total_paper_count=20, years_active=5)
        assert high > low


class TestComputeEvidenceQuality:
    """Evidence = cross-source corroboration count."""

    def test_no_sources(self):
        score = compute_evidence_quality(source_count=0)
        assert score == pytest.approx(0.0)

    def test_one_source(self):
        score = compute_evidence_quality(source_count=1)
        assert 0.0 < score <= 0.6

    def test_two_sources_higher(self):
        one = compute_evidence_quality(source_count=1)
        two = compute_evidence_quality(source_count=2)
        assert two > one

    def test_max_at_three_or_more(self):
        three = compute_evidence_quality(source_count=3)
        four = compute_evidence_quality(source_count=4)
        assert three == pytest.approx(four)
        assert three == pytest.approx(1.0)

    def test_score_in_range(self):
        for count in range(5):
            score = compute_evidence_quality(source_count=count)
            assert 0.0 <= score <= 1.0


class TestComputeCredibility:
    """Credibility = organisation prestige proxy."""

    def test_no_org_name_low_credibility(self):
        score = compute_credibility(org_name=None)
        assert score == pytest.approx(0.3)

    def test_known_elite_org_high(self):
        score = compute_credibility(org_name="MIT")
        assert score > 0.7

    def test_unknown_org_mid(self):
        score = compute_credibility(org_name="Some Random University")
        assert 0.3 < score <= 0.7

    def test_score_in_range(self):
        for org in [None, "MIT", "Stanford University", "XYZ Institute"]:
            score = compute_credibility(org_name=org)
            assert 0.0 <= score <= 1.0


class TestPersonFeatures:
    """Integration: PersonFeatures dataclass correctly bundles all signals."""

    def test_creation(self):
        pf = PersonFeatures(
            semantic_similarity=0.8,
            graph_proximity=0.5,
            novelty=0.6,
            growth=0.4,
            evidence_quality=0.7,
            credibility=0.9,
        )
        assert pf.semantic_similarity == pytest.approx(0.8)
        assert pf.graph_proximity == pytest.approx(0.5)

    def test_all_values_in_range(self):
        pf = PersonFeatures(
            semantic_similarity=0.5,
            graph_proximity=0.5,
            novelty=0.5,
            growth=0.5,
            evidence_quality=0.5,
            credibility=0.5,
        )
        for field in [
            "semantic_similarity",
            "graph_proximity",
            "novelty",
            "growth",
            "evidence_quality",
            "credibility",
        ]:
            val = getattr(pf, field)
            assert 0.0 <= val <= 1.0
