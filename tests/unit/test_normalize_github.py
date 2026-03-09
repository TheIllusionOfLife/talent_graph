"""TDD tests for GitHub → common schema normalizer."""

import json
from pathlib import Path

import pytest

from talent_graph.normalize.normalize_github import normalize_repo, normalize_github_user

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def repo_fixture() -> dict:
    return json.loads((FIXTURE_DIR / "github_repo.json").read_text())


@pytest.fixture
def user_fixture() -> dict:
    return json.loads((FIXTURE_DIR / "github_user.json").read_text())


@pytest.fixture
def contributors_fixture() -> list:
    return json.loads((FIXTURE_DIR / "github_contributors.json").read_text())


def test_normalize_repo_returns_repo_record(repo_fixture: dict) -> None:
    repo = normalize_repo(repo_fixture)
    assert repo.full_name == "octocat/Hello-World"
    assert repo.github_repo_id == 1296269
    assert repo.description == "My first repository on GitHub!"
    assert repo.language == "Python"
    assert repo.stars == 1234
    assert repo.forks == 567


def test_normalize_repo_extracts_topics(repo_fixture: dict) -> None:
    repo = normalize_repo(repo_fixture)
    assert "machine-learning" in repo.topics
    assert "python" in repo.topics


def test_normalize_repo_extracts_owner(repo_fixture: dict) -> None:
    repo = normalize_repo(repo_fixture)
    assert repo.owner_login == "octocat"
    assert repo.owner_type == "User"


def test_normalize_repo_with_contributors(
    repo_fixture: dict, contributors_fixture: list
) -> None:
    repo = normalize_repo(repo_fixture, contributors=contributors_fixture)
    # Bots excluded by default in normalizer
    assert "octocat" in repo.contributor_logins
    assert "contributor1" in repo.contributor_logins
    assert "bot-user" not in repo.contributor_logins


def test_normalize_repo_no_contributors(repo_fixture: dict) -> None:
    repo = normalize_repo(repo_fixture)
    assert repo.contributor_logins == []


def test_normalize_repo_handles_null_description(repo_fixture: dict) -> None:
    repo_fixture["description"] = None
    repo = normalize_repo(repo_fixture)
    assert repo.description is None


def test_normalize_repo_handles_null_language(repo_fixture: dict) -> None:
    repo_fixture["language"] = None
    repo = normalize_repo(repo_fixture)
    assert repo.language is None


def test_normalize_github_user_returns_person_record(user_fixture: dict) -> None:
    person = normalize_github_user(user_fixture)
    assert person.name == "The Octocat"
    assert person.github_login == "octocat"
    assert person.email == "octocat@github.com"


def test_normalize_github_user_null_email(user_fixture: dict) -> None:
    user_fixture["email"] = None
    person = normalize_github_user(user_fixture)
    assert person.email is None


def test_normalize_github_user_blog_as_homepage(user_fixture: dict) -> None:
    person = normalize_github_user(user_fixture)
    assert person.homepage == "https://github.blog"


def test_normalize_github_user_empty_blog(user_fixture: dict) -> None:
    user_fixture["blog"] = ""
    person = normalize_github_user(user_fixture)
    assert person.homepage is None
