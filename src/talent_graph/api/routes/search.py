"""GET /search — embed query and return ANN-ranked persons."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request

from talent_graph.api.deps import require_user_key
from talent_graph.api.limiter import limiter
from talent_graph.embeddings.generator import encode_one_async
from talent_graph.embeddings.text_builder import build_query_text
from talent_graph.storage.postgres import get_db_session
from talent_graph.storage.vector_store import search_similar

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    id: str
    name: str
    score: float  # cosine similarity (1 - distance)


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
        rows = await search_similar(session, query_vec, limit=limit)

    results = [
        SearchResult(
            id=row["id"],
            name=row["name"],
            score=round(1.0 - float(row["distance"]), 4),
        )
        for row in rows
    ]
    return SearchResponse(query=q, results=results)
