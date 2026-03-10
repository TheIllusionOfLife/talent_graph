"""Admin endpoints — all require API key."""

import re
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from starlette.requests import Request

from talent_graph.api.deps import require_api_key
from talent_graph.api.limiter import limiter
from talent_graph.ingestion.jobs import ingest_github, ingest_openalex
from talent_graph.storage.models import EntityLink, Paper, Person, Repo
from talent_graph.storage.postgres import get_db_session

_SLUG_RE = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_api_key)])


# ── Request / Response models ─────────────────────────────────────────────────


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

    @field_validator("repos", mode="before")
    @classmethod
    def validate_slugs(cls, v: list[str]) -> list[str]:
        for slug in v:
            if not _SLUG_RE.match(slug):
                raise ValueError(
                    f"Invalid repo slug {slug!r}. Expected format: 'owner/repo' "
                    "(alphanumeric, hyphens, underscores, dots only)."
                )
        return v


class EntityLinkOut(BaseModel):
    id: str
    person_id_a: str
    person_id_b: str
    confidence: float
    method: str
    status: str
    created_at: datetime


class EntityLinkPage(BaseModel):
    items: list[EntityLinkOut]
    total: int
    page: int
    page_size: int


class AdminStats(BaseModel):
    person_count: int
    paper_count: int
    repo_count: int
    pending_entity_links: int


# ── Ingest routes ─────────────────────────────────────────────────────────────


@router.post("/ingest/openalex", response_model=IngestResponse)
@limiter.limit("5/minute")
async def trigger_openalex_ingest(
    request: Request, body: OpenAlexIngestRequest, background_tasks: BackgroundTasks
) -> IngestResponse:
    """Queue an OpenAlex ingestion job. Returns immediately; runs in background."""
    background_tasks.add_task(ingest_openalex, query=body.query, max_results=body.max_results)
    return IngestResponse(
        status="accepted",
        message=f"Ingestion queued for query '{body.query}' (max_results={body.max_results})",
    )


@router.post("/ingest/github", response_model=IngestResponse)
@limiter.limit("5/minute")
async def trigger_github_ingest(
    request: Request, body: GitHubIngestRequest, background_tasks: BackgroundTasks
) -> IngestResponse:
    """Queue a GitHub ingestion job. Returns immediately; runs in background."""
    background_tasks.add_task(ingest_github, repos=body.repos)
    return IngestResponse(
        status="accepted",
        message=f"GitHub ingestion queued for {len(body.repos)} repo(s)",
    )


# ── Stats route ───────────────────────────────────────────────────────────────


@router.get("/stats", response_model=AdminStats)
@limiter.limit("60/minute")
async def get_stats(request: Request) -> AdminStats:
    """Return system-wide counts for the admin dashboard."""
    async with get_db_session() as session:
        person_count = (
            await session.execute(select(func.count()).select_from(Person))
        ).scalar_one()
        paper_count = (await session.execute(select(func.count()).select_from(Paper))).scalar_one()
        repo_count = (await session.execute(select(func.count()).select_from(Repo))).scalar_one()
        pending_links = (
            await session.execute(
                select(func.count()).select_from(EntityLink).where(EntityLink.status == "pending")
            )
        ).scalar_one()

    return AdminStats(
        person_count=person_count,
        paper_count=paper_count,
        repo_count=repo_count,
        pending_entity_links=pending_links,
    )


# ── Entity-links routes ───────────────────────────────────────────────────────


@router.get("/entity-links", response_model=EntityLinkPage)
@limiter.limit("60/minute")
async def list_entity_links(
    request: Request,
    status: Literal["pending", "merged", "rejected"] = Query(default="pending"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> EntityLinkPage:
    """List entity resolution candidates, paginated."""
    offset = (page - 1) * page_size
    async with get_db_session() as session:
        total = (
            await session.execute(
                select(func.count()).select_from(EntityLink).where(EntityLink.status == status)
            )
        ).scalar_one()
        result = await session.execute(
            select(EntityLink)
            .where(EntityLink.status == status)
            .order_by(EntityLink.confidence.desc(), EntityLink.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        links = result.scalars().all()

    return EntityLinkPage(
        items=[
            EntityLinkOut(
                id=lnk.id,
                person_id_a=lnk.person_id_a,
                person_id_b=lnk.person_id_b,
                confidence=lnk.confidence,
                method=lnk.method,
                status=lnk.status,
                created_at=lnk.created_at,
            )
            for lnk in links
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


async def _resolve_entity_link(
    link_id: str, new_status: Literal["merged", "rejected"]
) -> EntityLinkOut:
    """Shared helper: atomically transition a pending link to merged or rejected."""
    async with get_db_session() as session:
        result = await session.execute(
            select(EntityLink).where(EntityLink.id == link_id).with_for_update()
        )
        lnk = result.scalar_one_or_none()
        if lnk is None:
            raise HTTPException(status_code=404, detail="Entity link not found")
        if lnk.status != "pending":
            raise HTTPException(status_code=409, detail=f"Entity link is already '{lnk.status}'")
        lnk.status = new_status
        await session.flush()
        return EntityLinkOut(
            id=lnk.id,
            person_id_a=lnk.person_id_a,
            person_id_b=lnk.person_id_b,
            confidence=lnk.confidence,
            method=lnk.method,
            status=lnk.status,
            created_at=lnk.created_at,
        )


@router.post("/entity-links/{link_id}/approve", response_model=EntityLinkOut)
@limiter.limit("60/minute")
async def approve_entity_link(request: Request, link_id: str) -> EntityLinkOut:
    """Approve a pending entity link (marks as merged)."""
    return await _resolve_entity_link(link_id, "merged")


@router.post("/entity-links/{link_id}/reject", response_model=EntityLinkOut)
@limiter.limit("60/minute")
async def reject_entity_link(request: Request, link_id: str) -> EntityLinkOut:
    """Reject a pending entity link."""
    return await _resolve_entity_link(link_id, "rejected")
