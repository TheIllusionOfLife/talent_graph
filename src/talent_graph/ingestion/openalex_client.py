"""OpenAlex REST API client with retry and polite-pool support."""

from typing import Any, cast

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

BASE_URL = "https://api.openalex.org"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return isinstance(exc, httpx.TransportError)


class OpenAlexClient:
    def __init__(self, email: str = "", base_url: str = BASE_URL) -> None:
        self._email = email
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=30.0,
            headers={"User-Agent": f"talent-graph/0.1 (mailto:{email})"},
        )

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self._email:
            params["mailto"] = self._email
        if extra:
            params.update(extra)
        return params

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._client.get(path, params=self._params(params))
        response.raise_for_status()
        return cast("dict[str, Any]", response.json())

    async def get_works(
        self,
        query: str,
        per_page: int = 25,
        cursor: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch a single page of works matching *query*."""
        params: dict[str, Any] = {
            "search": query,
            "per_page": per_page,
            "cursor": cursor or "*",
        }
        data = await self._get("/works", params)
        return cast("list[dict[str, Any]]", data.get("results", []))

    async def get_works_paginated(
        self,
        query: str,
        max_results: int = 200,
        per_page: int = 25,
    ) -> list[dict[str, Any]]:
        """Fetch works across multiple pages until *max_results* reached."""
        results: list[dict[str, Any]] = []
        cursor: str | None = "*"

        while cursor and len(results) < max_results:
            params: dict[str, Any] = {
                "search": query,
                "per_page": min(per_page, max_results - len(results)),
                "cursor": cursor,
            }
            data = await self._get("/works", params)
            page = data.get("results", [])
            results.extend(page)
            cursor = data.get("meta", {}).get("next_cursor")
            if not page:
                break

        return results[:max_results]

    async def get_author(self, author_id: str) -> dict[str, Any]:
        """Fetch a single author by OpenAlex ID (with or without 'A' prefix)."""
        clean_id = author_id.lstrip("A") if author_id.startswith("A") else author_id
        return cast("dict[str, Any]", await self._get(f"/authors/A{clean_id}"))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "OpenAlexClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
