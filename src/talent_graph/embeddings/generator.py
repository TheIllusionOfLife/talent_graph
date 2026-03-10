"""Sentence-transformer embedding generation with lazy model loading."""

import asyncio
import threading

import structlog
from sentence_transformers import SentenceTransformer

from talent_graph.config.settings import get_settings

log = structlog.get_logger()

_model: SentenceTransformer | None = None
_model_lock = threading.Lock()


def get_model() -> SentenceTransformer:
    """Load model once; cached for the process lifetime (thread-safe)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # double-checked locking
                settings = get_settings()
                log.info("embeddings.model.loading", model=settings.embedding_model)
                _model = SentenceTransformer(settings.embedding_model)
                log.info("embeddings.model.ready", model=settings.embedding_model)
    return _model


def encode(texts: list[str]) -> list[list[float]]:
    """Encode a batch of texts; returns list of 384-dim float vectors."""
    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [vec.tolist() for vec in embeddings]


def encode_one(text: str) -> list[float]:
    """Encode a single text string."""
    return encode([text])[0]


async def encode_one_async(text: str) -> list[float]:
    """Async wrapper: runs encode_one in a thread pool to avoid blocking the event loop."""
    return await asyncio.to_thread(encode_one, text)
