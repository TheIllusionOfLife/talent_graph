"""GET /search — embed query and return ANN-ranked persons."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from talent_graph.api.deps import require_api_key
from talent_graph.embeddings.generator import encode_one
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


@router.get("", response_model=SearchResponse, dependencies=[Depends(require_api_key)])
async def search_persons(
    q: str = Query(..., min_length=1, max_length=2048, description="Free-text search query"),
    limit: int = Query(default=20, ge=1, le=100),
) -> SearchResponse:
    """Embed the query and return persons ranked by cosine similarity."""
    query_text = build_query_text(q)
    query_vec = encode_one(query_text)

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
