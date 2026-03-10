"""Saved search CRUD + run — /searches."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from talent_graph.api.deps import get_current_key
from talent_graph.config.settings import get_settings
from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import SavedSearch
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()
router = APIRouter(prefix="/searches", tags=["searches"])


def _owner_hash(api_key: str) -> str:
    secret = get_settings().app_secret.encode()
    return hmac.new(secret, api_key.encode(), hashlib.sha256).hexdigest()


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


@router.post("", status_code=201, response_model=SavedSearchOut)
async def create_saved_search(
    body: SavedSearchCreate,
    current_key: str = Depends(get_current_key),
) -> SavedSearchOut:
    search_id = new_id()
    now = datetime.now(UTC).replace(tzinfo=None)
    async with get_db_session() as session:
        search = SavedSearch(
            id=search_id,
            owner_key=_owner_hash(current_key),
            name=body.name,
            query=body.query,
            filters=body.filters,
            created_at=now,
        )
        session.add(search)
        await session.flush()
        return SavedSearchOut(
            id=search.id,
            name=search.name,
            query=search.query,
            filters=search.filters,
            created_at=search.created_at,
            last_run_at=search.last_run_at,
        )


@router.get("", response_model=list[SavedSearchOut])
async def list_saved_searches(
    current_key: str = Depends(get_current_key),
) -> list[SavedSearchOut]:
    async with get_db_session() as session:
        result = await session.execute(
            select(SavedSearch)
            .where(SavedSearch.owner_key == _owner_hash(current_key))
            .order_by(SavedSearch.created_at.desc())
        )
        searches = result.scalars().all()
    return [
        SavedSearchOut(
            id=s.id,
            name=s.name,
            query=s.query,
            filters=s.filters,
            created_at=s.created_at,
            last_run_at=s.last_run_at,
        )
        for s in searches
    ]


@router.get("/{search_id}", response_model=SavedSearchOut)
async def get_saved_search(
    search_id: str,
    current_key: str = Depends(get_current_key),
) -> SavedSearchOut:
    async with get_db_session() as session:
        result = await session.execute(
            select(SavedSearch).where(
                SavedSearch.id == search_id,
                SavedSearch.owner_key == _owner_hash(current_key),
            )
        )
        search = result.scalar_one_or_none()
    if search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return SavedSearchOut(
        id=search.id,
        name=search.name,
        query=search.query,
        filters=search.filters,
        created_at=search.created_at,
        last_run_at=search.last_run_at,
    )


@router.delete("/{search_id}", status_code=204)
async def delete_saved_search(
    search_id: str,
    current_key: str = Depends(get_current_key),
) -> None:
    async with get_db_session() as session:
        result = await session.execute(
            select(SavedSearch).where(
                SavedSearch.id == search_id,
                SavedSearch.owner_key == _owner_hash(current_key),
            )
        )
        search = result.scalar_one_or_none()
        if search is None:
            raise HTTPException(status_code=404, detail="Saved search not found")
        await session.delete(search)
