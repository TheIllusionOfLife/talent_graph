"""Deterministic entity resolution — exact-match on external IDs.

Priority order: openalex_author_id → ORCID → github_login → homepage (GitHub URL) → email.
All matches carry confidence = 1.0. Returns an existing canonical_person_id or None.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from talent_graph.normalize.common_schema import PersonRecord
from talent_graph.storage.models import Person

_GITHUB_URL_RE = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9\-]+)/?$", re.IGNORECASE)
_ORCID_BARE_RE = re.compile(r"(\d{4}-\d{4}-\d{4}-\d{3}[\dX])$", re.IGNORECASE)


def _normalize_orcid(orcid: str) -> str | None:
    """Strip any URL prefix and return the bare ORCID, or None if malformed."""
    m = _ORCID_BARE_RE.search(orcid)
    return m.group(1) if m else None


def _extract_github_login(url: str) -> str | None:
    """Extract GitHub username from a github.com URL, or return None."""
    m = _GITHUB_URL_RE.match(url.strip())
    return m.group(1) if m else None


async def resolve_deterministic(session: AsyncSession, person: PersonRecord) -> str | None:
    """Return existing canonical_person_id for the first deterministic match, else None.

    Priority order: openalex_author_id → ORCID → github_login → homepage → email.
    Stops at the first match to avoid unnecessary queries.
    """
    # 0. OpenAlex author ID — source-native stable ID, highest priority
    if person.openalex_author_id:
        result = await session.execute(
            select(Person.id).where(Person.openalex_author_id == person.openalex_author_id)
        )
        if found := result.scalar_one_or_none():
            return found

    # 1. ORCID match
    if person.orcid:
        bare = _normalize_orcid(person.orcid)
        if bare:
            result = await session.execute(select(Person.id).where(Person.orcid == bare))
            if found := result.scalar_one_or_none():
                return found

    # 2. Direct github_login match (case-insensitive — GitHub logins are case-insensitive)
    if person.github_login:
        result = await session.execute(
            select(Person.id).where(func.lower(Person.github_login) == person.github_login.lower())
        )
        if found := result.scalar_one_or_none():
            return found

    # 3. GitHub URL in OpenAlex homepage (case-insensitive login match)
    if person.homepage:
        login = _extract_github_login(person.homepage)
        if login:
            result = await session.execute(
                select(Person.id).where(func.lower(Person.github_login) == login.lower())
            )
            if found := result.scalar_one_or_none():
                return found

    # 4. Email match (case-insensitive; no unique constraint — use first() to avoid MultipleResultsFound)
    if person.email:
        normalized_email = person.email.strip().lower()
        result = await session.execute(
            select(Person.id).where(func.lower(Person.email) == normalized_email).limit(1)
        )
        if found := result.scalars().first():
            return found

    return None
