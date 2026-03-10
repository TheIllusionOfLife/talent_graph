"""TDD tests for explain/llm_client.py."""

from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import Response

from talent_graph.explain.llm_client import LLMClient, LLMUnavailableError

BASE_URL = "http://localhost:8080/v1"
CHAT_URL = f"{BASE_URL}/chat/completions"


class TestLLMClient:
    """Raw httpx LLM client tests."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_response(self):
        respx.post(CHAT_URL).mock(
            return_value=Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "Alice is a top researcher."}}
                    ]
                },
            )
        )
        client = LLMClient(base_url=BASE_URL, timeout=5)
        result = await client.complete("system prompt", "user prompt")
        assert "Alice" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_non_200_raises_llm_unavailable(self):
        respx.post(CHAT_URL).mock(return_value=Response(503, text="Service Unavailable"))
        client = LLMClient(base_url=BASE_URL, timeout=5)
        with pytest.raises(LLMUnavailableError):
            await client.complete("sys", "user")

    @respx.mock
    @pytest.mark.asyncio
    async def test_think_tags_stripped(self):
        content = "<think>internal reasoning here</think>Final answer about the candidate."
        respx.post(CHAT_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": content}}]},
            )
        )
        client = LLMClient(base_url=BASE_URL, timeout=5)
        result = await client.complete("sys", "user")
        assert "<think>" not in result
        assert "internal reasoning" not in result
        assert "Final answer" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_malformed_json_raises_llm_unavailable(self):
        respx.post(CHAT_URL).mock(return_value=Response(200, text="not-json"))
        client = LLMClient(base_url=BASE_URL, timeout=5)
        with pytest.raises(LLMUnavailableError):
            await client.complete("sys", "user")

    @respx.mock
    @pytest.mark.asyncio
    async def test_missing_choices_raises_llm_unavailable(self):
        respx.post(CHAT_URL).mock(
            return_value=Response(200, json={"choices": []})
        )
        client = LLMClient(base_url=BASE_URL, timeout=5)
        with pytest.raises(LLMUnavailableError):
            await client.complete("sys", "user")

    @pytest.mark.asyncio
    async def test_connection_error_raises_llm_unavailable(self):
        """Connection refused should raise LLMUnavailableError, not propagate ConnectError."""
        client = LLMClient(base_url="http://localhost:19999/v1", timeout=1)

        async def raise_connect_error(*args, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient.post", new=raise_connect_error), pytest.raises(LLMUnavailableError):
            await client.complete("sys", "user")

    @respx.mock
    @pytest.mark.asyncio
    async def test_enable_thinking_false_in_request(self):
        """Request body should contain enable_thinking=False."""
        captured = {}

        async def capture(request):
            import json
            captured["body"] = json.loads(request.content)
            return Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
            )

        respx.post(CHAT_URL).mock(side_effect=capture)
        client = LLMClient(base_url=BASE_URL, timeout=5)
        await client.complete("sys", "user")
        assert captured["body"].get("enable_thinking") is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_multiline_think_tags_stripped(self):
        content = "<think>\nsome\nmultiline\nreasoning\n</think>\n\nActual response content."
        respx.post(CHAT_URL).mock(
            return_value=Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": content}}]},
            )
        )
        client = LLMClient(base_url=BASE_URL, timeout=5)
        result = await client.complete("sys", "user")
        assert "<think>" not in result
        assert "Actual response" in result
