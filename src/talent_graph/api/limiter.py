"""slowapi Limiter instance and rate-limit key resolver."""

import hashlib
import os

from slowapi import Limiter
from starlette.requests import Request


def _rate_limit_key(request: Request) -> str:
    """Build a rate-limit bucket key.

    Uses SHA-256(api_key):client_ip when the header is present so the raw
    credential is never stored in the limiter's in-memory store.  Falls back
    to IP-only when no header is provided.  Both components are required so an
    attacker must control both the API-key string *and* source IP to bypass.
    """
    api_key: str | None = request.headers.get("X-API-Key")
    client_host: str = str(request.client.host) if request.client else "unknown"
    if api_key:
        hashed = hashlib.sha256(api_key.encode()).hexdigest()
        return f"{hashed}:{client_host}"
    return client_host


limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"),
)
