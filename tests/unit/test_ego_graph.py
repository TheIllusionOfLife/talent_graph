"""Unit tests for ego-graph helpers: compound ID generation, node config, edge canonicalization."""

import pytest

from talent_graph.api.routes.graph import (
    _build_compound_id,
    _canonicalize_links,
    _NODE_CONFIG,
    _transform_results,
)


class TestNodeConfig:
    """Verify _NODE_CONFIG covers all expected node types."""

    def test_all_node_types_present(self) -> None:
        expected = {"person", "paper", "concept", "org", "repo"}
        assert set(_NODE_CONFIG.keys()) == expected

    def test_each_config_has_required_keys(self) -> None:
        for node_type, cfg in _NODE_CONFIG.items():
            assert "label" in cfg, f"{node_type} missing 'label'"
            assert "id_field" in cfg, f"{node_type} missing 'id_field'"
            assert "model" in cfg, f"{node_type} missing 'model'"
            assert "key_attr" in cfg, f"{node_type} missing 'key_attr'"


class TestBuildCompoundId:
    """Verify compound ID format: {type_lower}__{natural_key}."""

    def test_person_id(self) -> None:
        assert _build_compound_id("Person", "abc123") == "person__abc123"

    def test_paper_id(self) -> None:
        assert _build_compound_id("Paper", "https://openalex.org/W123") == "paper__https://openalex.org/W123"

    def test_repo_id(self) -> None:
        assert _build_compound_id("Repo", "owner/repo") == "repo__owner/repo"

    def test_concept_id(self) -> None:
        assert _build_compound_id("Concept", "C123") == "concept__C123"

    def test_org_id(self) -> None:
        assert _build_compound_id("Org", "I999") == "org__I999"


class TestCanonicalizeLinks:
    """Verify edge deduplication for undirected relationships."""

    def test_dedup_bidirectional(self) -> None:
        links = [
            {"source": "person__a", "target": "person__b", "type": "COAUTHORED_WITH"},
            {"source": "person__b", "target": "person__a", "type": "COAUTHORED_WITH"},
        ]
        result = _canonicalize_links(links)
        assert len(result) == 1

    def test_preserves_different_types(self) -> None:
        links = [
            {"source": "person__a", "target": "paper__x", "type": "AUTHORED"},
            {"source": "person__a", "target": "org__y", "type": "AFFILIATED_WITH"},
        ]
        result = _canonicalize_links(links)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        assert _canonicalize_links([]) == []


class TestTransformResults:
    """Verify Neo4j raw result → EgoGraphResponse transformation."""

    def test_basic_transform(self) -> None:
        raw = {
            "nodes": [
                {
                    "type": "Person",
                    "node_key": "p1",
                    "label": "Alice",
                    "props": {"person_id": "p1", "name": "Alice"},
                },
                {
                    "type": "Paper",
                    "node_key": "W1",
                    "label": "Paper One",
                    "props": {"openalex_work_id": "W1", "title": "Paper One", "citation_count": 10},
                },
            ],
            "links": [
                {
                    "source_type": "Person",
                    "source_key": "p1",
                    "target_type": "Paper",
                    "target_key": "W1",
                    "rel_type": "AUTHORED",
                },
            ],
            "truncated": False,
        }
        response = _transform_results(raw, center_id="person__p1")

        assert response.center_id == "person__p1"
        assert len(response.nodes) == 2
        assert len(response.links) == 1
        assert response.truncated is False

        # Check compound IDs
        node_ids = {n.id for n in response.nodes}
        assert "person__p1" in node_ids
        assert "paper__W1" in node_ids

        # Check link compound IDs
        link = response.links[0]
        assert link.source == "person__p1"
        assert link.target == "paper__W1"
        assert link.type == "AUTHORED"

    def test_truncated_flag(self) -> None:
        raw = {
            "nodes": [
                {"type": "Person", "node_key": "p1", "label": "A", "props": {}},
            ],
            "links": [],
            "truncated": True,
        }
        response = _transform_results(raw, center_id="person__p1")
        assert response.truncated is True

    def test_empty_results(self) -> None:
        raw = {"nodes": [], "links": [], "truncated": False}
        response = _transform_results(raw, center_id="person__p1")
        assert len(response.nodes) == 0
        assert len(response.links) == 0
