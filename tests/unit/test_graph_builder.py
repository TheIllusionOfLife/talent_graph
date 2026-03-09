"""TDD tests for graph builder (idempotent MERGE operations)."""

from unittest.mock import AsyncMock, patch

import pytest

from talent_graph.graph.graph_builder import GraphBuilder
from talent_graph.normalize.common_schema import (
    AuthorPosition,
    ConceptRecord,
    OrgRecord,
    PaperRecord,
    PersonRecord,
)


@pytest.fixture
def builder() -> GraphBuilder:
    return GraphBuilder()


@pytest.fixture
def paper() -> PaperRecord:
    concept = ConceptRecord(
        openalex_concept_id="C119857082",
        name="Machine learning",
        level=1,
        score=0.95,
    )
    org = OrgRecord(
        name="Google Brain",
        openalex_institution_id="I1299303940",
        country_code="US",
    )
    person = PersonRecord(
        name="Ashish Vaswani",
        openalex_author_id="A5023888391",
        canonical_person_id="person_01JTEST000000001",
        org=org,
    )
    return PaperRecord(
        title="Attention Is All You Need",
        openalex_work_id="W2741809807",
        publication_year=2017,
        citation_count=95000,
        authors=[AuthorPosition(person=person, position=1, is_corresponding=False)],
        concepts=[concept],
    )


@pytest.mark.asyncio
async def test_upsert_paper_calls_merge_paper(builder: GraphBuilder, paper: PaperRecord) -> None:
    with patch(
        "talent_graph.graph.graph_builder.run_write_query", new_callable=AsyncMock
    ) as mock_q:
        mock_q.return_value = [{"openalex_work_id": "W2741809807"}]
        await builder.upsert_paper(paper)
        assert mock_q.called


@pytest.mark.asyncio
async def test_upsert_paper_merges_concept(builder: GraphBuilder, paper: PaperRecord) -> None:
    calls: list[str] = []

    async def capture(query: str, params: dict | None = None) -> list:
        calls.append(query)
        return []

    with patch("talent_graph.graph.graph_builder.run_write_query", side_effect=capture):
        await builder.upsert_paper(paper)

    # Should have called MERGE for concept
    assert any("Concept" in q for q in calls)


@pytest.mark.asyncio
async def test_upsert_paper_merges_org(builder: GraphBuilder, paper: PaperRecord) -> None:
    calls: list[str] = []

    async def capture(query: str, params: dict | None = None) -> list:
        calls.append(query)
        return []

    with patch("talent_graph.graph.graph_builder.run_write_query", side_effect=capture):
        await builder.upsert_paper(paper)

    assert any("Org" in q for q in calls)


@pytest.mark.asyncio
async def test_upsert_paper_merges_person(builder: GraphBuilder, paper: PaperRecord) -> None:
    calls: list[str] = []

    async def capture(query: str, params: dict | None = None) -> list:
        calls.append(query)
        return []

    with patch("talent_graph.graph.graph_builder.run_write_query", side_effect=capture):
        await builder.upsert_paper(paper)

    assert any("Person" in q for q in calls)


@pytest.mark.asyncio
async def test_upsert_paper_skips_author_without_canonical_id(
    builder: GraphBuilder, paper: PaperRecord
) -> None:
    """Authors without canonical_person_id should not be written to the graph."""
    paper.authors[0].person.canonical_person_id = None
    calls: list[str] = []

    async def capture(query: str, params: dict | None = None) -> list:
        calls.append(query)
        return []

    with patch("talent_graph.graph.graph_builder.run_write_query", side_effect=capture):
        await builder.upsert_paper(paper)

    # No AUTHORED relationship should be created
    assert not any("AUTHORED" in q for q in calls)


@pytest.mark.asyncio
async def test_upsert_paper_idempotent(builder: GraphBuilder, paper: PaperRecord) -> None:
    """Calling upsert_paper twice should not raise errors (MERGE is idempotent)."""
    with patch(
        "talent_graph.graph.graph_builder.run_write_query", new_callable=AsyncMock
    ) as mock_q:
        mock_q.return_value = []
        await builder.upsert_paper(paper)
        await builder.upsert_paper(paper)
        assert mock_q.call_count > 1
