"""Tests for RankingSignal model — Learning to Rank signal tracking."""

from talent_graph.storage.models import RankingSignal


class TestRankingSignalModel:
    """Verify RankingSignal model structure."""

    def test_create_save_signal(self) -> None:
        """Can create a RankingSignal with action='save'."""
        signal = RankingSignal(
            id="rs_001",
            person_id="p_abc",
            query="graph neural networks",
            action="save",
            context={"shortlist_id": "sl_123", "position": 0},
            owner_key="hashed_key",
        )
        assert signal.id == "rs_001"
        assert signal.person_id == "p_abc"
        assert signal.query == "graph neural networks"
        assert signal.action == "save"
        assert signal.context == {"shortlist_id": "sl_123", "position": 0}
        assert signal.owner_key == "hashed_key"

    def test_create_discard_signal(self) -> None:
        """Can create a RankingSignal with action='discard'."""
        signal = RankingSignal(
            id="rs_002",
            person_id="p_def",
            query="multimodal dialogue",
            action="discard",
            context={"shortlist_id": "sl_456"},
            owner_key="hashed_key",
        )
        assert signal.action == "discard"

    def test_context_is_optional(self) -> None:
        """Context JSONB field can be None."""
        signal = RankingSignal(
            id="rs_003",
            person_id="p_ghi",
            query="test",
            action="save",
            owner_key="key",
        )
        assert signal.context is None

    def test_tablename(self) -> None:
        """Model maps to ranking_signals table."""
        assert RankingSignal.__tablename__ == "ranking_signals"
