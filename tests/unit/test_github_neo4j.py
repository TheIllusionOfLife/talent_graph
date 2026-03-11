"""Tests for GitHub ingestion Neo4j node creation and contributor limits."""

from unittest.mock import AsyncMock, MagicMock, patch

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

    @pytest.mark.asyncio
    async def test_ingest_github_limits_contributors(self) -> None:
        """ingest_github should truncate contributors to max_contributors."""
        # Build 50 raw contributors (GitHub API returns sorted by contributions desc)
        raw_contributors = [{"login": f"user{i}", "contributions": 100 - i} for i in range(50)]

        # Mock GitHubClient
        mock_gh = AsyncMock()
        mock_gh.get_repo.return_value = {
            "full_name": "org/repo",
            "name": "repo",
            "owner": {"login": "org", "type": "Organization"},
            "description": "test",
            "language": "Python",
            "stargazers_count": 10,
            "forks_count": 2,
            "topics": [],
        }
        mock_gh.get_contributors.return_value = raw_contributors
        # get_user returns minimal user data for each contributor
        mock_gh.get_user.side_effect = lambda login: {
            "login": login,
            "name": login.title(),
            "bio": "",
            "company": None,
            "location": None,
            "public_repos": 5,
            "followers": 1,
        }
        mock_gh.__aenter__ = AsyncMock(return_value=mock_gh)
        mock_gh.__aexit__ = AsyncMock(return_value=False)

        # Mock DB and Neo4j dependencies
        mock_session = AsyncMock()
        mock_db_ctx = AsyncMock()
        mock_db_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_settings = MagicMock()
        mock_settings.github_token = "test-token"

        user_calls: list[str] = []
        original_get_user = mock_gh.get_user.side_effect

        async def tracking_get_user(login: str) -> dict[str, object]:
            user_calls.append(login)
            return dict(original_get_user(login))

        mock_gh.get_user.side_effect = tracking_get_user

        with (
            patch(
                "talent_graph.ingestion.jobs.GitHubClient",
                return_value=mock_gh,
            ),
            patch("talent_graph.ingestion.jobs.get_settings", return_value=mock_settings),
            patch("talent_graph.ingestion.jobs.get_db_session", return_value=mock_db_ctx),
            patch("talent_graph.ingestion.jobs.resolve_person", return_value="pid"),
            patch("talent_graph.ingestion.jobs.upsert_person"),
            patch("talent_graph.ingestion.jobs.write_heuristic_links"),
            patch("talent_graph.ingestion.jobs.upsert_repo", return_value="repo-id"),
            patch("talent_graph.ingestion.jobs.upsert_repo_contributor"),
            patch("talent_graph.ingestion.jobs.GraphBuilder") as mock_builder_cls,
        ):
            mock_builder_cls.return_value.upsert_repo = AsyncMock()
            from talent_graph.ingestion.jobs import ingest_github

            await ingest_github(["org/repo"], max_contributors=10)

        # Only 10 user profiles should have been fetched (owner is org, skipped)
        assert len(user_calls) == 10
        # Should be the top-10 contributors (user0..user9), order may vary (set iteration)
        assert set(user_calls) == {f"user{i}" for i in range(10)}
