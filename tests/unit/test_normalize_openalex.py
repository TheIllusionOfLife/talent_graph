"""TDD tests for OpenAlex → common schema normalizer."""

import json
from pathlib import Path

import pytest

from talent_graph.normalize.normalize_openalex import normalize_work

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def work_fixture() -> dict:
    return json.loads((FIXTURE_DIR / "openalex_work.json").read_text())


def test_normalize_work_returns_paper_record(work_fixture: dict) -> None:
    paper = normalize_work(work_fixture)
    assert paper.openalex_work_id == "W2741809807"
    assert paper.title == "Attention Is All You Need"
    assert paper.publication_year == 2017
    assert paper.citation_count == 95000


def test_normalize_work_extracts_doi(work_fixture: dict) -> None:
    paper = normalize_work(work_fixture)
    assert paper.doi == "https://doi.org/10.48550/arXiv.1706.03762"


def test_normalize_work_extracts_authors(work_fixture: dict) -> None:
    paper = normalize_work(work_fixture)
    assert len(paper.authors) == 2
    first = paper.authors[0]
    assert first.person.name == "Ashish Vaswani"
    assert first.person.openalex_author_id == "A5023888391"
    assert first.position == 1
    assert first.is_corresponding is False


def test_normalize_work_extracts_author_org(work_fixture: dict) -> None:
    paper = normalize_work(work_fixture)
    org = paper.authors[0].person.org
    assert org is not None
    assert org.name == "Google Brain"
    assert org.openalex_institution_id == "I1299303940"
    assert org.country_code == "US"


def test_normalize_work_extracts_concepts(work_fixture: dict) -> None:
    paper = normalize_work(work_fixture)
    assert len(paper.concepts) == 2
    ml_concept = next(c for c in paper.concepts if c.name == "Machine learning")
    assert ml_concept.openalex_concept_id == "C119857082"
    assert ml_concept.level == 1
    assert abs(ml_concept.score - 0.95) < 1e-6


def test_normalize_work_handles_missing_doi(work_fixture: dict) -> None:
    work_fixture.pop("doi", None)
    paper = normalize_work(work_fixture)
    assert paper.doi is None


def test_normalize_work_handles_empty_authorships(work_fixture: dict) -> None:
    work_fixture["authorships"] = []
    paper = normalize_work(work_fixture)
    assert paper.authors == []


def test_normalize_work_author_position_string_first(work_fixture: dict) -> None:
    """Author positions are assigned sequentially by order of appearance (1-based)."""
    paper = normalize_work(work_fixture)
    positions = [a.position for a in paper.authors]
    assert positions[0] == 1  # "first"
    assert positions[1] == 2  # "middle"


def test_normalize_work_strips_openalex_url_prefix(work_fixture: dict) -> None:
    """IDs like 'https://openalex.org/W123' should be stored as 'W123'."""
    paper = normalize_work(work_fixture)
    assert paper.openalex_work_id is not None
    assert not paper.openalex_work_id.startswith("http")
    assert paper.openalex_work_id == "W2741809807"


def test_normalize_work_reconstructs_abstract(work_fixture: dict) -> None:
    """abstract_inverted_index is reconstructed into plaintext."""
    paper = normalize_work(work_fixture)
    # Fixture has {"The": [0], "dominant": [1], "sequence": [2], "transduction": [3]}
    assert paper.abstract == "The dominant sequence transduction"


def test_normalize_work_abstract_none_when_missing(work_fixture: dict) -> None:
    work_fixture.pop("abstract_inverted_index", None)
    paper = normalize_work(work_fixture)
    assert paper.abstract is None


def test_normalize_work_middle_authors_preserve_order(work_fixture: dict) -> None:
    """Multiple 'middle' authors must get distinct sequential positions."""
    work_fixture["authorships"] = [
        {
            "author_position": "first",
            "author": {"id": "https://openalex.org/A1", "display_name": "Author One"},
            "institutions": [],
            "is_corresponding": False,
        },
        {
            "author_position": "middle",
            "author": {"id": "https://openalex.org/A2", "display_name": "Author Two"},
            "institutions": [],
            "is_corresponding": False,
        },
        {
            "author_position": "middle",
            "author": {"id": "https://openalex.org/A3", "display_name": "Author Three"},
            "institutions": [],
            "is_corresponding": False,
        },
        {
            "author_position": "last",
            "author": {"id": "https://openalex.org/A4", "display_name": "Author Four"},
            "institutions": [],
            "is_corresponding": False,
        },
    ]
    paper = normalize_work(work_fixture)
    positions = [a.position for a in paper.authors]
    assert positions == [1, 2, 3, 4], f"Expected [1,2,3,4] but got {positions}"
