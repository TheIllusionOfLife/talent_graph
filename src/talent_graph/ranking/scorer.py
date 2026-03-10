"""Multi-signal weighted linear ranking scorer."""

from talent_graph.features.person_features import PersonFeatures
from talent_graph.ranking.modes import RankMode

WEIGHTS: dict[RankMode, dict[str, float]] = {
    RankMode.STANDARD: {
        "semantic_similarity": 0.30,
        "graph_proximity": 0.20,
        "novelty": 0.15,
        "growth": 0.15,
        "evidence_quality": 0.10,
        "credibility": 0.10,
    },
    RankMode.HIDDEN: {
        "semantic_similarity": 0.20,
        "graph_proximity": 0.10,
        "novelty": 0.25,
        "growth": 0.10,
        "evidence_quality": 0.20,
        "credibility": 0.15,
    },
    RankMode.EMERGING: {
        "semantic_similarity": 0.25,
        "graph_proximity": 0.15,
        "novelty": 0.10,
        "growth": 0.30,
        "evidence_quality": 0.10,
        "credibility": 0.10,
    },
}


def score_candidate(features: PersonFeatures, mode: RankMode) -> float:
    """Compute weighted linear combination score in [0, 1]."""
    w = WEIGHTS[mode]
    return float(
        w["semantic_similarity"] * features.semantic_similarity
        + w["graph_proximity"] * features.graph_proximity
        + w["novelty"] * features.novelty
        + w["growth"] * features.growth
        + w["evidence_quality"] * features.evidence_quality
        + w["credibility"] * features.credibility
    )
