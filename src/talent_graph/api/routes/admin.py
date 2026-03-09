"""Admin endpoints — all require API key."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from talent_graph.api.deps import require_api_key
from talent_graph.ingestion.jobs import ingest_openalex

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_api_key)])


class IngestRequest(BaseModel):
    query: str
    max_results: int = 100


class IngestResponse(BaseModel):
    status: str
    counts: dict[str, int]


@router.post("/ingest/openalex", response_model=IngestResponse)
async def trigger_openalex_ingest(body: IngestRequest) -> IngestResponse:
    counts = await ingest_openalex(query=body.query, max_results=body.max_results)
    return IngestResponse(status="ok", counts=counts)
