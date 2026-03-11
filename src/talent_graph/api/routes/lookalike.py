"""GET /lookalike/{person_id} — find similar persons by embedding distance."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request

from talent_graph.api.deps import require_user_key
from talent_graph.api.limiter import limiter
from talent_graph.storage.models import Person
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.vector_store import search_similar

router = APIRouter(prefix="/lookalike", tags=["lookalike"])


# ── Response models ───────────────────────────────────────────────────────


class LookalikeResult(BaseModel):
    id: str
    name: str
    similarity: float  # 1 - cosine_distance


class LookalikeResponse(BaseModel):
    person_id: str
    results: list[LookalikeResult]


# ── Helpers ───────────────────────────────────────────────────────────────


def _build_results(rows: list[dict], exclude_id: str) -> list[LookalikeResult]:
    """Transform vector store rows, excluding self and clamping similarity."""
    results: list[LookalikeResult] = []
    for row in rows:
        if row["id"] == exclude_id:
            continue
        similarity = max(0.0, 1.0 - row["distance"])
        results.append(
            LookalikeResult(id=row["id"], name=row["name"], similarity=round(similarity, 4))
        )
    return results


# ── Route ─────────────────────────────────────────────────────────────────


@router.get(
    "/{person_id}",
    response_model=LookalikeResponse,
    dependencies=[Depends(require_user_key)],
)
@limiter.limit("30/minute")
async def get_lookalikes(
    request: Request,
    person_id: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> LookalikeResponse:
    """Find persons with similar embeddings to the given person."""
    async with get_db_session() as session:
        person = await session.get(Person, person_id)
        if person is None:
            raise HTTPException(status_code=404, detail="Person not found")

        if person.embedding is None:
            return LookalikeResponse(person_id=person_id, results=[])

        # Fetch limit+1 to account for self being in results
        try:
            rows = await search_similar(session, list(person.embedding), limit=limit + 1)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Vector search unavailable") from exc

    results = _build_results(rows, exclude_id=person_id)
    return LookalikeResponse(person_id=person_id, results=results[:limit])
