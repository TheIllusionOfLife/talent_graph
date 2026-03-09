"""GitHub REST API client with retry and token authentication."""

from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

BASE_URL = "https://api.github.com"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {500, 502, 503, 504}
    return isinstance(exc, httpx.TransportError)


class GitHubClient:
    def __init__(self, token: str = "", base_url: str = BASE_URL) -> None:
        self._base_url = base_url.rstrip("/")
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "talent-graph/0.1",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30.0,
            headers=headers,
        )

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = await self._client.get(path, params=params or {})
        response.raise_for_status()
        return response.json()

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository metadata."""
        return await self._get(f"/repos/{owner}/{repo}")

    async def get_contributors(
        self,
        owner: str,
        repo: str,
        per_page: int = 100,
        exclude_bots: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch top contributors for a repository."""
        data: list[dict[str, Any]] = await self._get(
            f"/repos/{owner}/{repo}/contributors",
            params={"per_page": per_page, "anon": "false"},
        )
        if exclude_bots:
            data = [c for c in data if c.get("type", "").lower() != "bot"]
        return data

    async def get_user(self, username: str) -> dict[str, Any]:
        """Fetch a GitHub user's public profile."""
        return await self._get(f"/users/{username}")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
