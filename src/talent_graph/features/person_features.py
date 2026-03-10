"""Feature engineering for person ranking signals."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Fallback set used before DB prestige table is loaded (tests / early startup)
_ELITE_ORGS_FALLBACK: frozenset[str] = frozenset(
    {
        "mit",
        "stanford",
        "harvard",
        "caltech",
        "oxford",
        "cambridge",
        "berkeley",
        "princeton",
        "carnegie mellon",
        "cmu",
        "eth zurich",
        "epfl",
        "toronto",
        "deepmind",
        "google research",
        "microsoft research",
        "meta ai",
        "openai",
        "anthropic",
    }
)

# Module-level cache — populated once at startup via init_prestige_names().
# None means "not yet loaded"; compute_credibility falls back to _ELITE_ORGS_FALLBACK.
_prestige_names: frozenset[str] | None = None


async def init_prestige_names() -> None:
    """Load prestige_orgs table into module-level frozenset (called once at startup)."""
    global _prestige_names
    try:
        from sqlalchemy import select

        from talent_graph.storage.models import PrestigeOrg
        from talent_graph.storage.postgres import get_db_session

        async with get_db_session() as session:
            result = await session.execute(select(PrestigeOrg.name))
            rows = result.scalars().all()
        _prestige_names = frozenset(rows)
    except Exception:
        # DB not available (e.g. tests without DB) — keep None so fallback is used
        pass


def _prestige_set() -> frozenset[str]:
    return _prestige_names if _prestige_names is not None else _ELITE_ORGS_FALLBACK


@dataclass
class PersonFeatures:
    """All ranking signals for one candidate, each in [0, 1]."""

    semantic_similarity: float
    graph_proximity: float
    novelty: float
    growth: float
    evidence_quality: float
    credibility: float


def compute_novelty(citation_count: int, paper_count: int) -> float:
    """Inverse citation prominence — uncited hidden experts score high.

    Uses log-damped inverse so a single very-cited paper doesn't dominate.
    Score is in [0, 1].
    """
    if citation_count <= 0:
        return 1.0
    # Normalise by paper count to get per-paper average, then apply log scale
    per_paper = citation_count / max(paper_count, 1)
    # log1p keeps it smooth; divide by a reference ceiling (1000 citations/paper)
    raw = math.log1p(per_paper) / math.log1p(1000)
    return max(0.0, 1.0 - min(raw, 1.0))


def compute_growth(recent_paper_count: int, total_paper_count: int, years_active: int) -> float:
    """Recent paper velocity as a fraction of total activity.

    recent_paper_count: papers in the last 2 years.
    total_paper_count: all-time paper count.
    years_active: career length in years.
    Score is in [0, 1].
    """
    if total_paper_count <= 0 and recent_paper_count <= 0:
        return 0.0

    # Recency ratio: what fraction of output is recent?
    total = max(total_paper_count, recent_paper_count)
    recency_ratio = recent_paper_count / total

    # Annual velocity: normalize by career length to detect acceleration.
    # Ceiling: 5 papers/year is considered high output.
    annual_velocity = recent_paper_count / max(years_active, 1)
    velocity = math.log1p(annual_velocity) / math.log1p(5)

    return min(1.0, 0.6 * recency_ratio + 0.4 * velocity)


def compute_evidence_quality(source_count: int) -> float:
    """Cross-source corroboration count mapped to [0, 1].

    0 sources → 0.0, 1 source → 0.5, 2 sources → 0.75, ≥3 sources → 1.0.
    """
    if source_count <= 0:
        return 0.0
    if source_count >= 3:
        return 1.0
    # Linear interpolation between 0.5 (1 source) and 1.0 (3 sources)
    return 0.5 + (source_count - 1) * 0.25


def compute_credibility(org_name: str | None) -> float:
    """Organisation prestige proxy using DB-backed prestige_orgs table.

    Known prestige orgs → 0.9, no org → 0.3, others → 0.5.
    Matching is case-insensitive substring check against the preloaded frozenset.
    """
    if org_name is None:
        return 0.3
    lower = org_name.lower().strip()
    prestige = _prestige_set()
    for name in prestige:
        if name in lower:
            return 0.9
    return 0.5
