"""Shortlist CRUD routes — /shortlists."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from talent_graph.api.deps import get_current_key
from talent_graph.config.settings import get_settings
from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import Person, Shortlist, ShortlistItem
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()
router = APIRouter(prefix="/shortlists", tags=["shortlists"])


def _owner_hash(api_key: str) -> str:
    """Return an HMAC-SHA256 digest of the API key using the configured app secret.

    Never stores the raw key — only this digest is persisted and compared.
    """
    secret = get_settings().app_secret.encode()
    return hmac.new(secret, api_key.encode(), hashlib.sha256).hexdigest()


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


@router.post("", status_code=201, response_model=ShortlistOut)
async def create_shortlist(
    body: ShortlistCreate,
    current_key: str = Depends(get_current_key),
) -> ShortlistOut:
    """Create a new shortlist owned by the caller's API key."""
    shortlist_id = f"sl_{new_id()}"
    now = datetime.now(UTC).replace(tzinfo=None)
    async with get_db_session() as session:
        sl = Shortlist(
            id=shortlist_id,
            name=body.name,
            description=body.description,
            owner_key=_owner_hash(current_key),
            created_at=now,
            updated_at=now,
        )
        session.add(sl)
        await session.flush()
        return _shortlist_to_out(sl)


@router.get("", response_model=list[ShortlistSummary])
async def list_shortlists(
    current_key: str = Depends(get_current_key),
) -> list[ShortlistSummary]:
    """List shortlists owned by the caller (with item counts)."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Shortlist, func.count(ShortlistItem.person_id).label("item_count"))
            .outerjoin(ShortlistItem, ShortlistItem.shortlist_id == Shortlist.id)
            .where(Shortlist.owner_key == _owner_hash(current_key))
            .group_by(Shortlist.id)
            .order_by(Shortlist.created_at.desc())
        )
        rows = result.all()

    return [
        ShortlistSummary(
            id=sl.id,
            name=sl.name,
            description=sl.description,
            created_at=sl.created_at,
            item_count=count,
        )
        for sl, count in rows
    ]


@router.get("/{shortlist_id}", response_model=ShortlistOut)
async def get_shortlist(
    shortlist_id: str,
    current_key: str = Depends(get_current_key),
) -> ShortlistOut:
    """Get shortlist detail (must belong to caller)."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Shortlist)
            .options(selectinload(Shortlist.items).selectinload(ShortlistItem.person))
            .where(Shortlist.id == shortlist_id, Shortlist.owner_key == _owner_hash(current_key))
        )
        sl = result.scalar_one_or_none()

    if sl is None:
        raise HTTPException(status_code=404, detail="Shortlist not found")

    return _shortlist_to_out(sl)


@router.delete("/{shortlist_id}", status_code=204)
async def delete_shortlist(
    shortlist_id: str,
    current_key: str = Depends(get_current_key),
) -> None:
    """Delete shortlist owned by the caller (cascades to items)."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Shortlist).where(
                Shortlist.id == shortlist_id, Shortlist.owner_key == _owner_hash(current_key)
            )
        )
        sl = result.scalar_one_or_none()
        if sl is None:
            raise HTTPException(status_code=404, detail="Shortlist not found")
        await session.delete(sl)


@router.post(
    "/{shortlist_id}/items",
    status_code=201,
    response_model=ShortlistItemOut,
)
async def add_item(
    shortlist_id: str,
    body: ShortlistItemCreate,
    current_key: str = Depends(get_current_key),
) -> ShortlistItemOut:
    """Add a person to a shortlist owned by the caller."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Shortlist).where(
                Shortlist.id == shortlist_id, Shortlist.owner_key == _owner_hash(current_key)
            )
        )
        sl = result.scalar_one_or_none()
        if sl is None:
            raise HTTPException(status_code=404, detail="Shortlist not found")

        person = await session.get(Person, body.person_id)
        if person is None:
            raise HTTPException(status_code=404, detail="Person not found")

        now = datetime.now(UTC).replace(tzinfo=None)
        item = ShortlistItem(
            shortlist_id=shortlist_id,
            person_id=body.person_id,
            note=body.note,
            position=0,
            added_at=now,
        )
        session.add(item)
        try:
            await session.flush()
        except IntegrityError as exc:
            # Unwrap to check for unique violation specifically
            orig = getattr(exc, "orig", None)
            if isinstance(orig, asyncpg.exceptions.UniqueViolationError):
                raise HTTPException(status_code=409, detail="Person already in shortlist") from exc
            raise

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


@router.delete("/{shortlist_id}/items/{person_id}", status_code=204)
async def remove_item(
    shortlist_id: str,
    person_id: str,
    current_key: str = Depends(get_current_key),
) -> None:
    """Remove a person from a shortlist owned by the caller."""
    async with get_db_session() as session:
        result = await session.execute(
            select(Shortlist).where(
                Shortlist.id == shortlist_id, Shortlist.owner_key == _owner_hash(current_key)
            )
        )
        sl = result.scalar_one_or_none()
        if sl is None:
            raise HTTPException(status_code=404, detail="Shortlist not found")

        item_result = await session.execute(
            select(ShortlistItem).where(
                ShortlistItem.shortlist_id == shortlist_id,
                ShortlistItem.person_id == person_id,
            )
        )
        item = item_result.scalar_one_or_none()
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
        created_at=sl.created_at,
        updated_at=sl.updated_at,
        items=items,
    )
