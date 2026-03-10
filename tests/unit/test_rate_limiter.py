"""Unit tests for _rate_limit_key()."""

import hashlib
from unittest.mock import MagicMock

from talent_graph.api.limiter import _rate_limit_key


def _make_request(api_key: str | None, client_host: str | None) -> MagicMock:
    request = MagicMock()
    request.headers.get = lambda h, d=None: api_key if h == "X-API-Key" else d
    if client_host is None:
        request.client = None
    else:
        request.client = MagicMock()
        request.client.host = client_host
    return request


def test_api_key_header_present() -> None:
    """Key is SHA-256(api_key):client_ip — raw secret is never stored."""
    request = _make_request(api_key="my-secret-key", client_host="1.2.3.4")
    expected_hash = hashlib.sha256(b"my-secret-key").hexdigest()
    assert _rate_limit_key(request) == f"{expected_hash}:1.2.3.4"


def test_no_header_uses_client_ip() -> None:
    request = _make_request(api_key=None, client_host="1.2.3.4")
    assert _rate_limit_key(request) == "1.2.3.4"


def test_no_client_returns_unknown() -> None:
    request = _make_request(api_key=None, client_host=None)
    assert _rate_limit_key(request) == "unknown"
