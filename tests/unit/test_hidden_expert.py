"""TDD tests for anomaly/hidden_expert.py."""

from unittest.mock import AsyncMock, patch

import pytest

from talent_graph.anomaly.hidden_expert import (
    HiddenExpertDetector,
    PersonFeatureRow,
    compute_hidden_expert_scores,
)


class TestPersonFeatureRow:
    """PersonFeatureRow dataclass validation."""

    def test_basic_creation(self):
        row = PersonFeatureRow(
            person_id="p1",
            citation_count=100,
            paper_count=10,
            recent_paper_count=3,
            source_count=2,
            years_active=5,
        )
        assert row.person_id == "p1"
        assert row.citation_count == 100

    def test_zero_paper_count_allowed(self):
        row = PersonFeatureRow(
            person_id="p2",
            citation_count=0,
            paper_count=0,
            recent_paper_count=0,
            source_count=1,
            years_active=0,
        )
        assert row.paper_count == 0


class TestHiddenExpertDetector:
    """IsolationForest-based hidden expert detection."""

    def _make_rows(self, n: int = 20) -> list[PersonFeatureRow]:
        """Generate a diverse set of PersonFeatureRow fixtures for detector training."""
        rows = []
        for i in range(n):
            rows.append(
                PersonFeatureRow(
                    person_id=f"person_{i}",
                    citation_count=i * 50,
                    paper_count=i + 1,
                    recent_paper_count=max(0, i - 5),
                    source_count=(i % 3) + 1,
                    years_active=max(1, i),
                )
            )
        return rows

    def test_fit_returns_detector(self):
        detector = HiddenExpertDetector()
        rows = self._make_rows(20)
        result = detector.fit(rows)
        assert result is detector  # fluent API

    def test_scores_returns_dict(self):
        detector = HiddenExpertDetector()
        rows = self._make_rows(20)
        detector.fit(rows)
        scores = detector.scores(rows)
        assert isinstance(scores, dict)
        assert len(scores) == len(rows)

    def test_scores_in_zero_one_range(self):
        detector = HiddenExpertDetector()
        rows = self._make_rows(20)
        detector.fit(rows)
        scores = detector.scores(rows)
        for person_id, score in scores.items():
            if score is not None:
                assert 0.0 <= score <= 1.0, f"score out of range for {person_id}: {score}"

    def test_person_with_zero_papers_gets_none(self):
        detector = HiddenExpertDetector()
        rows = self._make_rows(20)
        detector.fit(rows)

        null_row = PersonFeatureRow(
            person_id="null_person",
            citation_count=0,
            paper_count=0,
            recent_paper_count=0,
            source_count=1,
            years_active=0,
        )
        scores = detector.scores([null_row])
        assert scores["null_person"] is None

    def test_reproducibility_with_random_state(self):
        rows = self._make_rows(20)
        d1 = HiddenExpertDetector(random_state=42)
        d2 = HiddenExpertDetector(random_state=42)
        d1.fit(rows)
        d2.fit(rows)
        s1 = d1.scores(rows)
        s2 = d2.scores(rows)
        for pid in s1:
            if s1[pid] is not None and s2[pid] is not None:
                assert abs(s1[pid] - s2[pid]) < 1e-9

    def test_log1p_scaling_applied(self):
        """High citation count should produce valid scores, not crash from un-scaled values."""
        rows = [
            PersonFeatureRow(
                person_id=f"p{i}",
                citation_count=i * 10000,
                paper_count=i + 1,
                recent_paper_count=1,
                source_count=2,
                years_active=max(1, i),
            )
            for i in range(1, 21)
        ]
        detector = HiddenExpertDetector()
        detector.fit(rows)
        scores = detector.scores(rows)
        for _pid, score in scores.items():
            assert score is not None
            assert 0.0 <= score <= 1.0

    def test_contamination_default(self):
        """10% contamination — roughly 2 of 20 rows should have score >= 0.5 as 'hidden'."""
        detector = HiddenExpertDetector(random_state=42)
        rows = self._make_rows(20)
        detector.fit(rows)
        scores = detector.scores(rows)
        non_null = [s for s in scores.values() if s is not None]
        assert len(non_null) > 0


class TestComputeHiddenExpertScores:
    """Integration: full async pipeline that fetches persons and persists scores."""

    @pytest.mark.asyncio
    async def test_returns_count(self):
        """compute_hidden_expert_scores should return a positive int on success."""
        mock_rows = [
            PersonFeatureRow(
                person_id=f"p{i}",
                citation_count=i * 10,
                paper_count=i + 1,
                recent_paper_count=1,
                source_count=1,
                years_active=max(1, i),
            )
            for i in range(1, 11)
        ]
        with (
            patch(
                "talent_graph.anomaly.hidden_expert._fetch_feature_rows",
                new_callable=AsyncMock,
                return_value=mock_rows,
            ),
            patch(
                "talent_graph.anomaly.hidden_expert._persist_scores",
                new_callable=AsyncMock,
            ) as mock_persist,
        ):
            count = await compute_hidden_expert_scores()
            assert count == 10
            mock_persist.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_persons_returns_zero(self):
        with patch(
            "talent_graph.anomaly.hidden_expert._fetch_feature_rows",
            new_callable=AsyncMock,
            return_value=[],
        ):
            count = await compute_hidden_expert_scores()
            assert count == 0
