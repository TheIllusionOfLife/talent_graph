"""Feature engineering for person ranking signals."""

import math
from dataclasses import dataclass

# Elite institutions used as credibility anchors (case-insensitive prefix match)
_ELITE_ORGS = {
    "mit", "stanford", "harvard", "caltech", "oxford", "cambridge",
    "berkeley", "princeton", "carnegie mellon", "cmu", "eth zurich",
    "epfl", "toronto", "deepmind", "google research", "microsoft research",
    "meta ai", "openai", "anthropic",
}


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

    # Velocity bonus: absolute recent output (log-damped)
    velocity = math.log1p(recent_paper_count) / math.log1p(20)  # 20 = high ceiling

    return min(1.0, 0.6 * recency_ratio + 0.4 * velocity)


def compute_evidence_quality(source_count: int) -> float:
    """Cross-source corroboration count mapped to [0, 1].

    0 sources → 0.0, 1 source → ~0.5, ≥3 sources → 1.0.
    """
    if source_count <= 0:
        return 0.0
    if source_count >= 3:
        return 1.0
    # Linear interpolation between 1 and 3
    return source_count / 3.0 * 1.0 + (1 - source_count / 3.0) * 0.0


def compute_credibility(org_name: str | None) -> float:
    """Organisation prestige proxy.

    Known elite orgs → 0.9, no org → 0.3, others → 0.5.
    """
    if org_name is None:
        return 0.3
    lower = org_name.lower()
    for elite in _ELITE_ORGS:
        if elite in lower:
            return 0.9
    return 0.5
