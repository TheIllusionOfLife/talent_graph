"""Shortlist CRUD routes — /shortlists."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from talent_graph.api.deps import require_api_key
from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import Person, Shortlist, ShortlistItem
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()
router = APIRouter(prefix="/shortlists", tags=["shortlists"])


# ── Request / Response models ────────────────────────────────────────────────


class ShortlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None


class ShortlistItemCreate(BaseModel):
    person_id: str
    note: str | None = None


class PersonSummary(BaseModel):
    id: str
    name: str
    openalex_author_id: str | None = None
    github_login: str | None = None


class ShortlistItemOut(BaseModel):
    person_id: str
    note: str | None = None
    position: int
    added_at: datetime
    person: PersonSummary | None = None


class ShortlistOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    owner_key: str
    created_at: datetime
    updated_at: datetime
    items: list[ShortlistItemOut] = []


class ShortlistSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: datetime
    item_count: int = 0


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post(
    "", status_code=201, response_model=ShortlistOut, dependencies=[Depends(require_api_key)]
)
async def create_shortlist(body: ShortlistCreate) -> ShortlistOut:
    """Create a new shortlist."""
    shortlist_id = f"sl_{new_id()}"
    now = datetime.now(UTC).replace(tzinfo=None)
    async with get_db_session() as session:
        sl = Shortlist(
            id=shortlist_id,
            name=body.name,
            description=body.description,
            owner_key="default",
            created_at=now,
            updated_at=now,
        )
        session.add(sl)
        await session.flush()
        return _shortlist_to_out(sl)


@router.get("", response_model=list[ShortlistSummary], dependencies=[Depends(require_api_key)])
async def list_shortlists() -> list[ShortlistSummary]:
    """List all shortlists."""
    async with get_db_session() as session:
        result = await session.execute(select(Shortlist).order_by(Shortlist.created_at.desc()))
        shortlists = result.scalars().all()

    summaries = []
    for sl in shortlists:
        summaries.append(
            ShortlistSummary(
                id=sl.id,
                name=sl.name,
                description=sl.description,
                created_at=sl.created_at,
                item_count=len(sl.items) if sl.items else 0,
            )
        )
    return summaries


@router.get("/{shortlist_id}", response_model=ShortlistOut, dependencies=[Depends(require_api_key)])
async def get_shortlist(shortlist_id: str) -> ShortlistOut:
    """Get shortlist detail with items and person summaries."""
    async with get_db_session() as session:
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            select(Shortlist)
            .options(selectinload(Shortlist.items).selectinload(ShortlistItem.person))
            .where(Shortlist.id == shortlist_id)
        )
        sl = result.scalar_one_or_none()

    if sl is None:
        raise HTTPException(status_code=404, detail="Shortlist not found")

    return _shortlist_to_out(sl)


@router.delete("/{shortlist_id}", status_code=204, dependencies=[Depends(require_api_key)])
async def delete_shortlist(shortlist_id: str) -> None:
    """Delete shortlist (cascades to items)."""
    async with get_db_session() as session:
        sl = await session.get(Shortlist, shortlist_id)
        if sl is None:
            raise HTTPException(status_code=404, detail="Shortlist not found")
        await session.delete(sl)


@router.post(
    "/{shortlist_id}/items",
    status_code=201,
    response_model=ShortlistItemOut,
    dependencies=[Depends(require_api_key)],
)
async def add_item(shortlist_id: str, body: ShortlistItemCreate) -> ShortlistItemOut:
    """Add a person to a shortlist."""
    async with get_db_session() as session:
        sl = await session.get(Shortlist, shortlist_id)
        if sl is None:
            raise HTTPException(status_code=404, detail="Shortlist not found")

        person = await session.get(Person, body.person_id)
        if person is None:
            raise HTTPException(status_code=404, detail="Person not found")

        # Check for duplicate
        dup_result = await session.execute(
            select(ShortlistItem).where(
                ShortlistItem.shortlist_id == shortlist_id,
                ShortlistItem.person_id == body.person_id,
            )
        )
        if dup_result.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Person already in shortlist")

        now = datetime.now(UTC).replace(tzinfo=None)
        item = ShortlistItem(
            shortlist_id=shortlist_id,
            person_id=body.person_id,
            note=body.note,
            position=0,
            added_at=now,
        )
        session.add(item)
        await session.flush()

        return ShortlistItemOut(
            person_id=item.person_id,
            note=item.note,
            position=item.position,
            added_at=item.added_at,
            person=PersonSummary(
                id=person.id,
                name=person.name,
                openalex_author_id=person.openalex_author_id,
                github_login=person.github_login,
            ),
        )


@router.delete(
    "/{shortlist_id}/items/{person_id}",
    status_code=204,
    dependencies=[Depends(require_api_key)],
)
async def remove_item(shortlist_id: str, person_id: str) -> None:
    """Remove a person from a shortlist."""
    async with get_db_session() as session:
        sl = await session.get(Shortlist, shortlist_id)
        if sl is None:
            raise HTTPException(status_code=404, detail="Shortlist not found")

        result = await session.execute(
            select(ShortlistItem).where(
                ShortlistItem.shortlist_id == shortlist_id,
                ShortlistItem.person_id == person_id,
            )
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail="Item not found in shortlist")
        await session.delete(item)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _shortlist_to_out(sl: Shortlist) -> ShortlistOut:
    items = []
    for item in sl.items or []:
        person_summary = None
        if hasattr(item, "person") and item.person:
            p = item.person
            person_summary = PersonSummary(
                id=p.id,
                name=p.name,
                openalex_author_id=p.openalex_author_id,
                github_login=p.github_login,
            )
        items.append(
            ShortlistItemOut(
                person_id=item.person_id,
                note=item.note,
                position=item.position,
                added_at=item.added_at,
                person=person_summary,
            )
        )
    return ShortlistOut(
        id=sl.id,
        name=sl.name,
        description=sl.description,
        owner_key=sl.owner_key,
        created_at=sl.created_at,
        updated_at=sl.updated_at,
        items=items,
    )
