"""Sentence-transformer embedding generation with lazy model loading."""

import structlog
from sentence_transformers import SentenceTransformer

from talent_graph.config.settings import get_settings

log = structlog.get_logger()

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Load model once; cached for the process lifetime."""
    global _model
    if _model is None:
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
