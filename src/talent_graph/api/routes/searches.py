"""Saved search CRUD + run — /searches."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from starlette.requests import Request  # noqa: TC002

from talent_graph.api.auth import owner_hash, require_any_api_key
from talent_graph.api.limiter import limiter
from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import SavedSearch
from talent_graph.storage.postgres import get_db_session

router = APIRouter(prefix="/searches", tags=["searches"])


class SavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    query: str = Field(..., min_length=1, max_length=2048)
    filters: dict | None = None


class SavedSearchOut(BaseModel):
    id: str
    name: str
    query: str
    filters: dict | None = None
    created_at: datetime
    last_run_at: datetime | None = None


def _to_out(search: SavedSearch) -> SavedSearchOut:
    return SavedSearchOut(
        id=search.id,
        name=search.name,
        query=search.query,
        filters=search.filters,
        created_at=search.created_at,
        last_run_at=search.last_run_at,
    )


@router.post("", status_code=201, response_model=SavedSearchOut)
@limiter.limit("60/minute")
async def create_saved_search(
    request: Request,
    body: SavedSearchCreate,
    current_key: str = Depends(require_any_api_key),
) -> SavedSearchOut:
    search_id = new_id()
    now = datetime.now(UTC).replace(tzinfo=None)
    async with get_db_session() as session:
        search = SavedSearch(
            id=search_id,
            owner_key=owner_hash(current_key),
            name=body.name,
            query=body.query,
            filters=body.filters,
            created_at=now,
        )
        session.add(search)
        await session.flush()
        return _to_out(search)


@router.get("", response_model=list[SavedSearchOut])
@limiter.limit("60/minute")
async def list_saved_searches(
    request: Request,
    current_key: str = Depends(require_any_api_key),
) -> list[SavedSearchOut]:
    async with get_db_session() as session:
        result = await session.execute(
            select(SavedSearch)
            .where(SavedSearch.owner_key == owner_hash(current_key))
            .order_by(SavedSearch.created_at.desc())
        )
        searches = result.scalars().all()
    return [_to_out(s) for s in searches]


@router.get("/{search_id}", response_model=SavedSearchOut)
@limiter.limit("60/minute")
async def get_saved_search(
    request: Request,
    search_id: str,
    current_key: str = Depends(require_any_api_key),
) -> SavedSearchOut:
    async with get_db_session() as session:
        result = await session.execute(
            select(SavedSearch).where(
                SavedSearch.id == search_id,
                SavedSearch.owner_key == owner_hash(current_key),
            )
        )
        search = result.scalar_one_or_none()
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return _to_out(search)


@router.delete("/{search_id}", status_code=204)
@limiter.limit("60/minute")
async def delete_saved_search(
    request: Request,
    search_id: str,
    current_key: str = Depends(require_any_api_key),
) -> None:
    async with get_db_session() as session:
        result = await session.execute(
            select(SavedSearch).where(
                SavedSearch.id == search_id,
                SavedSearch.owner_key == owner_hash(current_key),
            )
        )
        search = result.scalar_one_or_none()
        if search is None:
            raise HTTPException(status_code=404, detail="Saved search not found")
        await session.delete(search)
