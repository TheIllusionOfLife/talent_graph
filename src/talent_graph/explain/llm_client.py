"""Raw httpx client for OpenAI-compatible LLM API (MLX server).

Raises LLMUnavailableError on any failure so callers can fall back gracefully.
"""

from __future__ import annotations

import re

import httpx
import structlog

log = structlog.get_logger()

# Strips <think>...</think> blocks including multiline content
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


class LLMUnavailableError(Exception):
    """Raised when the LLM backend is unreachable, returns non-200, or times out."""


class LLMClient:
    """Thin async wrapper around an OpenAI-compatible /chat/completions endpoint."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        model: str = "mlx-community/Qwen3.5-35B-A3B-4bit",
        timeout: int = 60,
        max_tokens: int = 512,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the assistant message text.

        Raises:
            LLMUnavailableError: on connection error, timeout, non-200, or malformed response.
        """
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": 0.3,
            "enable_thinking": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url, json=payload)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError) as exc:
            log.warning("llm.request.failed", error=str(exc))
            raise LLMUnavailableError(str(exc)) from exc

        if response.status_code != 200:
            log.warning("llm.non_200", status=response.status_code)
            raise LLMUnavailableError(f"HTTP {response.status_code}")

        try:
            data = response.json()
            choices = data["choices"]
            if not choices:
                raise LLMUnavailableError("Empty choices in response")
            text: str = choices[0]["message"]["content"]
        except (KeyError, TypeError, ValueError) as exc:
            log.warning("llm.malformed_response", error=str(exc))
            raise LLMUnavailableError(f"Malformed response: {exc}") from exc

        return _strip_think_tags(text)


def _strip_think_tags(text: str) -> str:
    """Remove any <think>...</think> blocks from generated text."""
    return _THINK_RE.sub("", text).strip()
