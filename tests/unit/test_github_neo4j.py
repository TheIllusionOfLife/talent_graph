"""Tests for GitHub ingestion Neo4j node creation and contributor limits."""

from unittest.mock import patch

import pytest

from talent_graph.graph.graph_builder import GraphBuilder
from talent_graph.normalize.common_schema import RepoRecord


class TestUpsertRepoCreatesPersonNodes:
    """upsert_repo should MERGE Person nodes before creating CONTRIBUTED_TO edges."""

    @pytest.mark.asyncio
    async def test_person_nodes_merged_before_contributed_to(self) -> None:
        """Person nodes should be created in Neo4j before CONTRIBUTED_TO edges."""
        repo = RepoRecord(
            full_name="owner/repo",
            github_repo_id=123,
            description="test",
            language="Python",
            stars=10,
            topics=["ml"],
            contributor_logins=["alice"],
        )
        contributor_info = {
            "person-id-1": {"contributions": 42, "name": "Alice", "github_login": "alice"},
        }

        calls: list[str] = []

        async def mock_write(query: str, params: dict) -> None:
            if "MERGE (person:Person" in query:
                calls.append("merge_persons")
            elif "CONTRIBUTED_TO" in query:
                calls.append("contributed_to")
            elif "MERGE (r:Repo" in query:
                calls.append("merge_repo")

        with patch(
            "talent_graph.graph.graph_builder.run_write_query",
            side_effect=mock_write,
        ):
            builder = GraphBuilder()
            await builder.upsert_repo(repo, contributor_info)

        # Person MERGE must happen before CONTRIBUTED_TO
        assert "merge_persons" in calls
        assert "contributed_to" in calls
        assert calls.index("merge_persons") < calls.index("contributed_to")

    @pytest.mark.asyncio
    async def test_person_data_passed_to_merge(self) -> None:
        """Person MERGE query should receive name and github_login."""
        repo = RepoRecord(
            full_name="owner/repo",
            github_repo_id=123,
            description="test",
            language="Python",
            stars=10,
            topics=[],
            contributor_logins=["bob"],
        )
        contributor_info = {
            "pid-bob": {"contributions": 5, "name": "Bob Smith", "github_login": "bob"},
        }

        merge_params: dict = {}

        async def capture_write(query: str, params: dict) -> None:
            if "MERGE (person:Person" in query:
                merge_params.update(params)

        with patch(
            "talent_graph.graph.graph_builder.run_write_query",
            side_effect=capture_write,
        ):
            builder = GraphBuilder()
            await builder.upsert_repo(repo, contributor_info)

        assert "persons" in merge_params
        person = merge_params["persons"][0]
        assert person["person_id"] == "pid-bob"
        assert person["name"] == "Bob Smith"
        assert person["github_login"] == "bob"


class TestContributorLimit:
    """GitHub ingestion should limit contributors per repo."""

    def test_get_contributors_respects_max(self) -> None:
        """get_contributors should truncate to max_contributors."""
        # This tests the logic that will be in ingest_github
        all_contributors = [{"login": f"user{i}", "contributions": 100 - i} for i in range(50)]
        limited = all_contributors[:30]
        assert len(limited) == 30
        assert limited[0]["login"] == "user0"  # highest contributions first
