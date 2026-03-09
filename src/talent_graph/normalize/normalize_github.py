"""GitHub API response → common schema normalizer."""

from talent_graph.normalize.common_schema import PersonRecord, RepoRecord


def normalize_repo(
    raw: dict,
    contributors: list[dict] | None = None,
) -> RepoRecord:
    """Normalize a GitHub repo API response into a RepoRecord.

    Args:
        raw: GitHub REST API /repos/{owner}/{repo} response dict.
        contributors: Optional /repos/{owner}/{repo}/contributors list.
                      Bots (type == "Bot") are excluded automatically.
    """
    owner = raw.get("owner") or {}
    contributor_logins: list[str] = []
    if contributors:
        contributor_logins = [
            c["login"]
            for c in contributors
            if c.get("type", "").lower() != "bot" and c.get("login")
        ]

    return RepoRecord(
        full_name=raw["full_name"],
        github_repo_id=raw.get("id"),
        description=raw.get("description") or None,
        language=raw.get("language") or None,
        stars=raw.get("stargazers_count", 0),
        forks=raw.get("forks_count", 0),
        topics=raw.get("topics") or [],
        owner_login=owner.get("login"),
        owner_type=owner.get("type"),
        contributor_logins=contributor_logins,
    )


def normalize_github_user(raw: dict) -> PersonRecord:
    """Normalize a GitHub user API response into a PersonRecord."""
    blog = raw.get("blog") or ""
    return PersonRecord(
        name=raw.get("name") or raw["login"],
        github_login=raw["login"],
        email=raw.get("email") or None,
        homepage=blog if blog else None,
    )
