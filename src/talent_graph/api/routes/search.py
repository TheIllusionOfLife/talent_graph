"""GET /search — embed query and return ANN-ranked persons."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request

from talent_graph.api.deps import require_user_key
from talent_graph.api.limiter import limiter
from talent_graph.embeddings.generator import encode_one_async
from talent_graph.embeddings.text_builder import build_query_text
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.vector_store import search_by_name, search_similar

router = APIRouter(prefix="/search", tags=["search"])

_NAME_MATCH_DISTANCE = 0.1  # Boosted distance for name matches (lower = more relevant)


def _blend_results(
    vec_rows: list[dict],
    name_rows: list[dict],
    limit: int,
) -> list[dict]:
    """Merge vector search and name search results, deduplicating by person ID.

    Name matches get a boosted distance (_NAME_MATCH_DISTANCE) so they rank
    higher than weak vector hits. When a person appears in both, the better
    (lower) distance wins.
    """
    merged: dict[str, dict] = {}
    for row in vec_rows:
        merged[row["id"]] = row
    for row in name_rows:
        boosted = {**row, "distance": _NAME_MATCH_DISTANCE}
        if row["id"] not in merged or merged[row["id"]]["distance"] > _NAME_MATCH_DISTANCE:
            merged[row["id"]] = boosted
    return sorted(merged.values(), key=lambda r: r["distance"])[:limit]


class SearchResult(BaseModel):
    id: str
    name: str
    score: float  # relevance score (1 - distance); name matches use boosted distance


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


@router.get("", response_model=SearchResponse, dependencies=[Depends(require_user_key)])
@limiter.limit("30/minute")
async def search_persons(
    request: Request,
    q: str = Query(..., min_length=1, max_length=2048, description="Free-text search query"),
    limit: int = Query(default=20, ge=1, le=100),
) -> SearchResponse:
    """Embed the query and return persons ranked by cosine similarity."""
    query_text = build_query_text(q)
    if not query_text:
        raise HTTPException(status_code=422, detail="Query must not be blank")
    query_vec = await encode_one_async(query_text)

    async with get_db_session() as session:
        vec_rows, name_rows = await asyncio.gather(
            search_similar(session, query_vec, limit=limit),
            search_by_name(session, q.strip(), limit=limit),
        )

    rows = _blend_results(vec_rows, name_rows, limit=limit)

    results = [
        SearchResult(
            id=row["id"],
            name=row["name"],
            score=round(1.0 - float(row["distance"]), 4),
        )
        for row in rows
    ]
    return SearchResponse(query=q, results=results)
