"""slowapi Limiter instance and rate-limit key resolver."""

from slowapi import Limiter
from starlette.requests import Request


def _rate_limit_key(request: Request) -> str:
    """Use X-API-Key header as rate-limit identity; fall back to client IP."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    if request.client is None:
        return "unknown"
    return request.client.host


limiter = Limiter(key_func=_rate_limit_key)
