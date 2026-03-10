"""Async explanation engine with LRU cache, semaphore, and template fallback."""

from __future__ import annotations

import asyncio
import hashlib

import structlog

from talent_graph.config.settings import get_settings
from talent_graph.explain.llm_client import LLMClient, LLMUnavailableError
from talent_graph.explain.prompt_templates import (
    PROMPT_VERSION,
    build_brief_prompt,
    render_template_fallback,
)

log = structlog.get_logger()

_CACHE_MAXSIZE = 256


class ExplanationEngine:
    """Singleton engine: serializes LLM requests and caches results."""

    def __init__(self) -> None:
        settings = get_settings()
        self._llm = LLMClient(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout=settings.llm_timeout,
        )
        self._semaphore = asyncio.Semaphore(1)
        self._cache: dict[tuple, str] = {}

    def _cache_key(self, person: object, seed_text: str) -> tuple:
        settings = get_settings()
        seed_hash = hashlib.sha256(seed_text.encode()).hexdigest()[:16]
        updated_at = getattr(person, "updated_at", None)
        updated_str = updated_at.isoformat() if updated_at else ""
        # Include a fingerprint of the person's paper IDs so the cache is
        # invalidated when new papers are added (person.updated_at may not change).
        papers = getattr(person, "papers", []) or []
        paper_ids_hash = hashlib.sha256(
            ",".join(sorted(getattr(p, "id", "") for p in papers)).encode()
        ).hexdigest()[:8]
        return (
            person.id,
            seed_hash,
            PROMPT_VERSION,
            settings.llm_model,
            updated_str,
            paper_ids_hash,
        )

    async def explain(
        self,
        person: object,
        seed_text: str,
        score_breakdown: dict[str, float],
        hop_distance: int = 1,
    ) -> str:
        """Generate a brief explanation for a candidate.

        Returns cached result if available. Falls back to template if LLM unavailable.
        Never raises.
        """
        key = self._cache_key(person, seed_text)
        if key in self._cache:
            log.debug("explanation.cache_hit", person_id=person.id)
            # Move to end to maintain LRU order
            value = self._cache.pop(key)
            self._cache[key] = value
            return value

        # Evict oldest entry if cache is full
        if len(self._cache) >= _CACHE_MAXSIZE:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        system_prompt, user_prompt = build_brief_prompt(
            person, seed_text, hop_distance, score_breakdown
        )

        async with self._semaphore:
            try:
                text = await self._llm.complete(system_prompt, user_prompt)
                log.debug("explanation.llm_success", person_id=person.id)
            except LLMUnavailableError as exc:
                log.warning("explanation.fallback", person_id=person.id, reason=str(exc))
                text = render_template_fallback(person, score_breakdown)

        self._cache[key] = text
        return text


# Module-level singleton — created lazily on first use
_engine: ExplanationEngine | None = None


def _get_engine() -> ExplanationEngine:
    global _engine
    if _engine is None:
        _engine = ExplanationEngine()
    return _engine


async def explain(
    person: object,
    seed_text: str,
    score_breakdown: dict[str, float],
    hop_distance: int = 1,
) -> str:
    """Module-level convenience function. Uses the shared engine singleton."""
    return await _get_engine().explain(person, seed_text, score_breakdown, hop_distance)
