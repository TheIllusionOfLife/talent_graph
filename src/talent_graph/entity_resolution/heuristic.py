"""Heuristic entity resolution using Jaro-Winkler name similarity, org overlap, and concepts.

Confidence thresholds:
  >= 0.8 → auto-merge (returns existing canonical_person_id)
  0.5–0.8 → queue in entity_links for human review
  < 0.5  → no match
"""

import jellyfish

from talent_graph.normalize.common_schema import PersonRecord

# Weight coefficients — must sum to 1.0
_W_NAME = 0.60
_W_ORG = 0.20
_W_CONCEPT = 0.20

_NAME_THRESHOLD = 0.92
_ORG_THRESHOLD = 0.85
_AUTO_MERGE_THRESHOLD = 0.80
_QUEUE_THRESHOLD = 0.50


def compute_name_similarity(a: str, b: str) -> float:
    """Jaro-Winkler similarity between two name strings. Returns 0.0 for empty inputs."""
    if not a or not b:
        return 0.0
    return jellyfish.jaro_winkler_similarity(a.strip().lower(), b.strip().lower())


def compute_org_similarity(a: str | None, b: str | None) -> float:
    """Jaro-Winkler similarity between two org name strings. Returns 0.0 if either is None."""
    if not a or not b:
        return 0.0
    return jellyfish.jaro_winkler_similarity(a.strip().lower(), b.strip().lower())


def compute_concept_overlap(a: list[str], b: list[str]) -> float:
    """Jaccard similarity between two concept-ID lists. Returns 0.0 for empty inputs."""
    if not a or not b:
        return 0.0
    set_a = set(a)
    set_b = set(b)
    return len(set_a & set_b) / len(set_a | set_b)


def compute_heuristic_confidence(
    a: PersonRecord,
    b: PersonRecord,
    concepts_a: list[str],
    concepts_b: list[str],
) -> float:
    """Weighted confidence score combining name, org, and concept signals.

    Returns a float in [0.0, 1.0].
    """
    name_sim = compute_name_similarity(a.name, b.name)
    org_a = a.org.name if a.org else None
    org_b = b.org.name if b.org else None
    org_sim = compute_org_similarity(org_a, org_b)
    concept_sim = compute_concept_overlap(concepts_a, concepts_b)

    return _W_NAME * name_sim + _W_ORG * org_sim + _W_CONCEPT * concept_sim


def is_auto_merge(confidence: float) -> bool:
    return confidence >= _AUTO_MERGE_THRESHOLD


def is_queue_candidate(confidence: float) -> bool:
    return _QUEUE_THRESHOLD <= confidence < _AUTO_MERGE_THRESHOLD
