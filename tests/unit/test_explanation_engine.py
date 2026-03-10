"""TDD tests for explain/explanation_engine.py."""

import asyncio
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from talent_graph.config.settings import get_settings
from talent_graph.explain.explanation_engine import (
    ExplanationEngine,
    explain,
    explain_with_meta,
)
from talent_graph.explain.llm_client import LLMUnavailableError
from talent_graph.explain.prompt_templates import PROMPT_VERSION


def _make_person(
    person_id: str = "p1",
    name: str = "Alice Smith",
    updated_at: datetime | None = None,
) -> MagicMock:
    person = MagicMock()
    person.id = person_id
    person.name = name
    person.updated_at = updated_at or datetime(2025, 1, 1)
    person.papers = []
    person.org = None
    person.openalex_author_id = None
    person.github_login = None
    return person


def _make_score_breakdown() -> dict:
    return {
        "semantic_similarity": 0.8,
        "graph_proximity": 0.5,
        "novelty": 0.7,
        "growth": 0.4,
        "evidence_quality": 0.6,
        "credibility": 0.5,
    }


def _fresh_engine() -> ExplanationEngine:
    """Create an ExplanationEngine bypassing __init__ with a fresh cache."""
    engine = ExplanationEngine.__new__(ExplanationEngine)
    engine._semaphore = asyncio.Semaphore(1)
    engine._cache = {}
    return engine


class TestExplainFunction:
    """Module-level explain() function tests."""

    @pytest.mark.asyncio
    async def test_llm_success_path(self):
        person = _make_person()
        breakdown = _make_score_breakdown()

        with patch("talent_graph.explain.explanation_engine._engine") as mock_engine:
            mock_engine.explain = AsyncMock(return_value="Alice is a hidden expert in NLP.")
            result = await explain(person, "attention mechanism", breakdown)
            assert "Alice" in result

    @pytest.mark.asyncio
    async def test_llm_unavailable_falls_back_to_template(self):
        """Engine handles LLMUnavailableError internally — module-level explain() never raises."""
        person = _make_person()
        breakdown = _make_score_breakdown()

        import talent_graph.explain.explanation_engine as eng_module

        original_engine = eng_module._engine
        try:
            engine = _fresh_engine()
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(side_effect=LLMUnavailableError("offline"))
            engine._llm = mock_llm
            eng_module._engine = engine

            with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_p:
                mock_p.return_value = ("sys", "user")
                result = await explain(person, "attention mechanism", breakdown)

            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            eng_module._engine = original_engine


class TestExplainWithMeta:
    """Module-level explain_with_meta() tests."""

    @pytest.mark.asyncio
    async def test_returns_text_and_false_on_llm_success(self):
        import talent_graph.explain.explanation_engine as eng_module

        original_engine = eng_module._engine
        try:
            engine = _fresh_engine()
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(return_value="LLM explanation")
            engine._llm = mock_llm
            eng_module._engine = engine

            person = _make_person()
            breakdown = _make_score_breakdown()
            with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_p:
                mock_p.return_value = ("sys", "user")
                text, used_fallback = await explain_with_meta(person, "query", breakdown)

            assert text == "LLM explanation"
            assert used_fallback is False
        finally:
            eng_module._engine = original_engine

    @pytest.mark.asyncio
    async def test_returns_text_and_true_on_llm_unavailable(self):
        import talent_graph.explain.explanation_engine as eng_module

        original_engine = eng_module._engine
        try:
            engine = _fresh_engine()
            mock_llm = AsyncMock()
            mock_llm.complete = AsyncMock(side_effect=LLMUnavailableError("offline"))
            engine._llm = mock_llm
            eng_module._engine = engine

            person = _make_person()
            breakdown = _make_score_breakdown()
            with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_p:
                mock_p.return_value = ("sys", "user")
                text, used_fallback = await explain_with_meta(person, "query", breakdown)

            assert isinstance(text, str)
            assert len(text) > 0
            assert used_fallback is True
        finally:
            eng_module._engine = original_engine


class TestExplanationEngine:
    """ExplanationEngine class-level tests."""

    @pytest.mark.asyncio
    async def test_explain_calls_llm_client(self):
        engine = _fresh_engine()
        person = _make_person()
        breakdown = _make_score_breakdown()

        with (
            patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt,
            patch("talent_graph.explain.explanation_engine.LLMClient") as mock_client_class,
        ):
            mock_prompt.return_value = ("system content", "user content")
            mock_instance = AsyncMock()
            mock_instance.complete = AsyncMock(return_value="LLM explanation text")
            mock_client_class.return_value = mock_instance

            engine._llm = mock_instance
            result = await engine.explain(person, "multimodal", breakdown)
            assert result == "LLM explanation text"
            mock_instance.complete.assert_awaited_once_with("system content", "user content")

    @pytest.mark.asyncio
    async def test_explain_with_meta_returns_tuple(self):
        engine = _fresh_engine()
        person = _make_person()
        breakdown = _make_score_breakdown()

        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value="meta explanation")
        engine._llm = mock_llm

        with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt:
            mock_prompt.return_value = ("sys", "user")
            text, used_fallback = await engine.explain_with_meta(person, "query", breakdown)

        assert text == "meta explanation"
        assert used_fallback is False

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(self):
        engine = _fresh_engine()
        person = _make_person()
        breakdown = _make_score_breakdown()
        cached_text = "Cached explanation"

        settings = get_settings()
        seed_hash = hashlib.sha256(b"attention mechanism").hexdigest()[:16]
        paper_ids_hash = hashlib.sha256(b"").hexdigest()[:8]
        cache_key = (
            person.id,
            seed_hash,
            PROMPT_VERSION,
            settings.llm_model,
            person.updated_at.isoformat(),
            paper_ids_hash,
        )
        # Cache stores (text, used_fallback) tuples
        engine._cache = {cache_key: (cached_text, False)}

        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value="NEW explanation")
        engine._llm = mock_llm

        result = await engine.explain(person, "attention mechanism", breakdown)
        assert result == cached_text
        mock_llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_hit_returns_correct_fallback_flag(self):
        engine = _fresh_engine()
        person = _make_person()
        breakdown = _make_score_breakdown()

        settings = get_settings()
        seed_hash = hashlib.sha256(b"query").hexdigest()[:16]
        paper_ids_hash = hashlib.sha256(b"").hexdigest()[:8]
        cache_key = (
            person.id,
            seed_hash,
            PROMPT_VERSION,
            settings.llm_model,
            person.updated_at.isoformat(),
            paper_ids_hash,
        )
        engine._cache = {cache_key: ("fallback text", True)}

        mock_llm = AsyncMock()
        engine._llm = mock_llm

        text, used_fallback = await engine.explain_with_meta(person, "query", breakdown)
        assert text == "fallback text"
        assert used_fallback is True
        mock_llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_key_includes_updated_at(self):
        engine = _fresh_engine()
        person_v1 = _make_person(updated_at=datetime(2025, 1, 1))
        person_v2 = _make_person(updated_at=datetime(2025, 6, 1))
        breakdown = _make_score_breakdown()

        call_count = 0

        async def mock_complete(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return f"explanation {call_count}"

        mock_llm = AsyncMock()
        mock_llm.complete = mock_complete
        engine._llm = mock_llm

        with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt:
            mock_prompt.return_value = ("sys", "user")
            r1 = await engine.explain(person_v1, "nlp", breakdown)
            r2 = await engine.explain(person_v2, "nlp", breakdown)

        assert r1 != r2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_semaphore_serializes_requests(self):
        engine = _fresh_engine()
        person = _make_person()
        breakdown = _make_score_breakdown()

        concurrent_count = 0
        max_concurrent = 0

        async def mock_complete(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return "result"

        mock_llm = MagicMock()
        mock_llm.complete = mock_complete
        engine._llm = mock_llm

        with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt:
            mock_prompt.return_value = ("sys", "user")
            person2 = _make_person(person_id="p2", name="Bob")
            await asyncio.gather(
                engine.explain(person, "nlp", breakdown),
                engine.explain(person2, "nlp", breakdown),
            )

        assert max_concurrent <= 1

    @pytest.mark.asyncio
    async def test_llm_unavailable_returns_template_fallback(self):
        engine = _fresh_engine()
        person = _make_person()
        breakdown = _make_score_breakdown()

        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(side_effect=LLMUnavailableError("offline"))
        engine._llm = mock_llm

        with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt:
            mock_prompt.return_value = ("sys", "user")
            result = await engine.explain(person, "nlp", breakdown)

        assert isinstance(result, str)
        assert len(result) > 10

    @pytest.mark.asyncio
    async def test_llm_unavailable_sets_fallback_flag(self):
        engine = _fresh_engine()
        person = _make_person()
        breakdown = _make_score_breakdown()

        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(side_effect=LLMUnavailableError("offline"))
        engine._llm = mock_llm

        with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt:
            mock_prompt.return_value = ("sys", "user")
            text, used_fallback = await engine.explain_with_meta(person, "nlp", breakdown)

        assert used_fallback is True
        assert len(text) > 10
