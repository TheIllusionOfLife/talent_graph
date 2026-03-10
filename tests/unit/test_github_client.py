"""TDD tests for GitHub REST API client."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
import respx
from httpx import Response

from talent_graph.ingestion.github_client import GitHubClient

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def repo_fixture() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((FIXTURE_DIR / "github_repo.json").read_text()))


@pytest.fixture
def user_fixture() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((FIXTURE_DIR / "github_user.json").read_text()))


@pytest.fixture
def contributors_fixture() -> list[Any]:
    return cast("list[Any]", json.loads((FIXTURE_DIR / "github_contributors.json").read_text()))


@pytest.fixture
def client() -> GitHubClient:
    return GitHubClient(token="ghp_test_token")


@respx.mock
@pytest.mark.asyncio
async def test_get_repo_returns_dict(client: GitHubClient, repo_fixture: dict) -> None:
    respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
        return_value=Response(200, json=repo_fixture)
    )
    repo = await client.get_repo("octocat", "Hello-World")
    assert repo["full_name"] == "octocat/Hello-World"
    assert repo["id"] == 1296269


@respx.mock
@pytest.mark.asyncio
async def test_get_repo_sends_auth_header(client: GitHubClient, repo_fixture: dict) -> None:
    route = respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
        return_value=Response(200, json=repo_fixture)
    )
    await client.get_repo("octocat", "Hello-World")
    assert "Authorization" in route.calls[0].request.headers
    assert "ghp_test_token" in route.calls[0].request.headers["Authorization"]


@respx.mock
@pytest.mark.asyncio
async def test_get_contributors_returns_list(
    client: GitHubClient, contributors_fixture: list
) -> None:
    respx.get("https://api.github.com/repos/octocat/Hello-World/contributors").mock(
        return_value=Response(200, json=contributors_fixture)
    )
    contributors = await client.get_contributors("octocat", "Hello-World")
    assert len(contributors) == 3
    assert contributors[0]["login"] == "octocat"
    assert contributors[0]["contributions"] == 100


@respx.mock
@pytest.mark.asyncio
async def test_get_contributors_filters_bots(
    client: GitHubClient, contributors_fixture: list
) -> None:
    respx.get("https://api.github.com/repos/octocat/Hello-World/contributors").mock(
        return_value=Response(200, json=contributors_fixture)
    )
    contributors = await client.get_contributors("octocat", "Hello-World", exclude_bots=True)
    logins = [c["login"] for c in contributors]
    assert "bot-user" not in logins
    assert "octocat" in logins


@respx.mock
@pytest.mark.asyncio
async def test_get_user_returns_dict(client: GitHubClient, user_fixture: dict) -> None:
    respx.get("https://api.github.com/users/octocat").mock(
        return_value=Response(200, json=user_fixture)
    )
    user = await client.get_user("octocat")
    assert user["login"] == "octocat"
    assert user["name"] == "The Octocat"


@respx.mock
@pytest.mark.asyncio
async def test_get_repo_retries_on_503(client: GitHubClient, repo_fixture: dict) -> None:
    respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
        side_effect=[
            Response(503, text="Service Unavailable"),
            Response(200, json=repo_fixture),
        ]
    )
    repo = await client.get_repo("octocat", "Hello-World")
    assert repo["full_name"] == "octocat/Hello-World"


@respx.mock
@pytest.mark.asyncio
async def test_get_repo_no_token_omits_auth(repo_fixture: dict) -> None:
    client_no_token = GitHubClient(token="")
    route = respx.get("https://api.github.com/repos/octocat/Hello-World").mock(
        return_value=Response(200, json=repo_fixture)
    )
    await client_no_token.get_repo("octocat", "Hello-World")
    assert "Authorization" not in route.calls[0].request.headers
