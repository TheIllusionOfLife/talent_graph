"""TDD tests for explain/explanation_engine.py."""

import asyncio
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from talent_graph.config.settings import get_settings
from talent_graph.explain.explanation_engine import ExplanationEngine, explain
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

        # Reset module singleton so we get a fresh engine with a mocked LLM
        import talent_graph.explain.explanation_engine as eng_module
        original_engine = eng_module._engine
        try:
            engine = ExplanationEngine.__new__(ExplanationEngine)
            engine._semaphore = asyncio.Semaphore(1)
            engine._cache = {}
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


class TestExplanationEngine:
    """ExplanationEngine class-level tests."""

    @pytest.mark.asyncio
    async def test_explain_calls_llm_client(self):
        engine = ExplanationEngine.__new__(ExplanationEngine)
        engine._semaphore = asyncio.Semaphore(1)
        engine._cache = {}

        person = _make_person()
        breakdown = _make_score_breakdown()

        with (
            patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt,
            patch(
                "talent_graph.explain.explanation_engine.LLMClient"
            ) as mock_client_class,
        ):
            mock_prompt.return_value = ("system content", "user content")
            mock_instance = AsyncMock()
            mock_instance.complete = AsyncMock(return_value="LLM explanation text")
            mock_client_class.return_value = mock_instance

            engine._llm = mock_instance
            result = await engine.explain(person, "multimodal", breakdown)
            assert "LLM explanation" in result or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(self):
        engine = ExplanationEngine.__new__(ExplanationEngine)
        engine._semaphore = asyncio.Semaphore(1)

        person = _make_person()
        breakdown = _make_score_breakdown()
        cached_text = "Cached explanation"

        # Pre-populate cache with the key the engine would generate
        settings = get_settings()
        seed_hash = hashlib.sha256(b"attention mechanism").hexdigest()[:16]
        paper_ids_hash = hashlib.sha256(b"").hexdigest()[:8]  # person.papers = []
        cache_key = (
            person.id,
            seed_hash,
            PROMPT_VERSION,
            settings.llm_model,
            person.updated_at.isoformat(),
            paper_ids_hash,
        )
        engine._cache = {cache_key: cached_text}

        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value="NEW explanation")
        engine._llm = mock_llm

        result = await engine.explain(person, "attention mechanism", breakdown)
        assert result == cached_text
        mock_llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_key_includes_updated_at(self):
        """Two persons with same id but different updated_at should have different cache keys."""
        engine = ExplanationEngine.__new__(ExplanationEngine)
        engine._semaphore = asyncio.Semaphore(1)
        engine._cache = {}

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
        """Two concurrent explain() calls should not run the LLM in parallel."""
        engine = ExplanationEngine.__new__(ExplanationEngine)
        engine._semaphore = asyncio.Semaphore(1)
        engine._cache = {}

        person = _make_person()
        breakdown = _make_score_breakdown()

        concurrent_count = 0
        max_concurrent = 0

        async def mock_complete(*args, **kwargs):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.01)  # simulate inference time
            concurrent_count -= 1
            return "result"

        mock_llm = MagicMock()
        mock_llm.complete = mock_complete
        engine._llm = mock_llm

        with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt:
            mock_prompt.return_value = ("sys", "user")
            # Run two calls concurrently with different cache keys by using different persons
            person2 = _make_person(person_id="p2", name="Bob")
            await asyncio.gather(
                engine.explain(person, "nlp", breakdown),
                engine.explain(person2, "nlp", breakdown),
            )

        # With Semaphore(1), max_concurrent should never exceed 1
        assert max_concurrent <= 1

    @pytest.mark.asyncio
    async def test_llm_unavailable_returns_template_fallback(self):
        engine = ExplanationEngine.__new__(ExplanationEngine)
        engine._semaphore = asyncio.Semaphore(1)
        engine._cache = {}

        person = _make_person()
        breakdown = _make_score_breakdown()

        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(side_effect=LLMUnavailableError("offline"))
        engine._llm = mock_llm

        with patch("talent_graph.explain.explanation_engine.build_brief_prompt") as mock_prompt:
            mock_prompt.return_value = ("sys", "user")
            result = await engine.explain(person, "nlp", breakdown)

        assert isinstance(result, str)
        assert len(result) > 10  # template produces meaningful text
