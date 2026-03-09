"""Admin endpoints — all require API key."""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from talent_graph.api.deps import require_api_key
from talent_graph.ingestion.jobs import ingest_github, ingest_openalex

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_api_key)])


class IngestResponse(BaseModel):
    status: str
    message: str


class OpenAlexIngestRequest(BaseModel):
    query: str
    max_results: int = Field(default=100, ge=1, le=1000)


class GitHubIngestRequest(BaseModel):
    repos: list[str] = Field(
        description="List of 'owner/repo' slugs to ingest.",
        min_length=1,
    )


@router.post("/ingest/openalex", response_model=IngestResponse)
async def trigger_openalex_ingest(
    body: OpenAlexIngestRequest, background_tasks: BackgroundTasks
) -> IngestResponse:
    """Queue an OpenAlex ingestion job. Returns immediately; runs in background."""
    background_tasks.add_task(ingest_openalex, query=body.query, max_results=body.max_results)
    return IngestResponse(
        status="accepted",
        message=f"Ingestion queued for query '{body.query}' (max_results={body.max_results})",
    )


@router.post("/ingest/github", response_model=IngestResponse)
async def trigger_github_ingest(
    body: GitHubIngestRequest, background_tasks: BackgroundTasks
) -> IngestResponse:
    """Queue a GitHub ingestion job. Returns immediately; runs in background."""
    background_tasks.add_task(ingest_github, repos=body.repos)
    return IngestResponse(
        status="accepted",
        message=f"GitHub ingestion queued for {len(body.repos)} repo(s)",
    )
