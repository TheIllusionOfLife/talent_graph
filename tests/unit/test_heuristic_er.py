"""TDD tests for heuristic entity resolution."""

import pytest

from talent_graph.entity_resolution.heuristic import (
    compute_concept_overlap,
    compute_heuristic_confidence,
    compute_name_similarity,
    compute_org_similarity,
)
from talent_graph.normalize.common_schema import OrgRecord, PersonRecord


def test_name_similarity_identical() -> None:
    assert compute_name_similarity("Alice Smith", "Alice Smith") == pytest.approx(1.0)


def test_name_similarity_high_jaro_winkler() -> None:
    # Near-identical names (middle initial variant) should score >= 0.92
    score = compute_name_similarity("Geoffrey Hinton", "Geoffrey E. Hinton")
    assert score >= 0.92


def test_name_similarity_different_names() -> None:
    score = compute_name_similarity("Alice Smith", "Bob Jones")
    assert score < 0.92


def test_name_similarity_empty_strings() -> None:
    assert compute_name_similarity("", "") == 0.0


def test_name_similarity_one_empty() -> None:
    assert compute_name_similarity("Alice", "") == 0.0


def test_org_similarity_identical() -> None:
    assert compute_org_similarity("MIT", "MIT") == pytest.approx(1.0)


def test_org_similarity_low_for_acronym_vs_full_name() -> None:
    score = compute_org_similarity("Massachusetts Institute of Technology", "MIT")
    # Acronym vs full name — below the 0.85 org-match threshold, should not auto-match
    assert isinstance(score, float)
    assert score < 0.85


def test_org_similarity_both_none() -> None:
    assert compute_org_similarity(None, None) == 0.0


def test_org_similarity_one_none() -> None:
    assert compute_org_similarity("MIT", None) == 0.0


def test_concept_overlap_identical() -> None:
    concepts = ["C1", "C2", "C3"]
    assert compute_concept_overlap(concepts, concepts) == pytest.approx(1.0)


def test_concept_overlap_partial() -> None:
    a = ["C1", "C2", "C3"]
    b = ["C2", "C3", "C4"]
    # intersection=2, union=4 → jaccard=0.5
    assert compute_concept_overlap(a, b) == pytest.approx(0.5)


def test_concept_overlap_no_overlap() -> None:
    assert compute_concept_overlap(["C1"], ["C2"]) == pytest.approx(0.0)


def test_concept_overlap_both_empty() -> None:
    assert compute_concept_overlap([], []) == 0.0


def test_heuristic_confidence_high_name_match() -> None:
    a = PersonRecord(
        name="Yann LeCun",
        org=OrgRecord(name="New York University"),
    )
    b = PersonRecord(
        name="Yann LeCun",
        org=OrgRecord(name="New York University"),
    )
    conf = compute_heuristic_confidence(a, b, concepts_a=[], concepts_b=[])
    assert conf >= 0.8


def test_heuristic_confidence_low_name_match() -> None:
    a = PersonRecord(name="Alice Smith")
    b = PersonRecord(name="Bob Jones")
    conf = compute_heuristic_confidence(a, b, concepts_a=[], concepts_b=[])
    assert conf < 0.5


def test_heuristic_confidence_returns_float_in_range() -> None:
    a = PersonRecord(name="Geoffrey Hinton", org=OrgRecord(name="University of Toronto"))
    b = PersonRecord(name="Geoffrey E. Hinton", org=OrgRecord(name="Univ. of Toronto"))
    conf = compute_heuristic_confidence(a, b, concepts_a=["C1", "C2"], concepts_b=["C1", "C3"])
    assert 0.0 <= conf <= 1.0


def test_heuristic_confidence_concept_boost() -> None:
    """Concept overlap should boost confidence for similar names."""
    a = PersonRecord(name="John Smith")
    b = PersonRecord(name="John Smith")
    conf_no_concepts = compute_heuristic_confidence(a, b, concepts_a=[], concepts_b=[])
    conf_with_concepts = compute_heuristic_confidence(
        a, b, concepts_a=["C1", "C2", "C3"], concepts_b=["C1", "C2", "C3"]
    )
    assert conf_with_concepts > conf_no_concepts
