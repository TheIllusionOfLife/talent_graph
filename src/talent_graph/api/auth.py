"""API key authentication."""

import hashlib
import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from talent_graph.config.settings import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def owner_hash(api_key: str) -> str:
    """Return an HMAC-SHA256 digest of the API key using the configured app secret.

    Never stores the raw key — only this digest is persisted and compared.
    Used by multi-tenant routes (shortlists, saved searches).
    """
    secret = get_settings().app_secret.encode()
    return hmac.new(secret, api_key.encode(), hashlib.sha256).hexdigest()


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """Dependency: validates X-API-Key header. Raises 401 if missing/invalid."""
    settings = get_settings()
    if not api_key or not hmac.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


async def require_any_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """Dependency: accepts any non-empty API key (treats each key as a distinct user identity).

    Use this on multi-tenant routes (e.g. shortlists, saved searches) where each caller's
    key is hashed to derive an owner token, enabling per-user isolation without a user registry.
    Raises 401 only when no key is provided.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


# RBAC aliases — admin routes require exact configured key; user routes accept any non-empty key.
require_admin_key = require_api_key
require_user_key = require_any_api_key


async def require_api_key_returning(
    api_key: str | None = Security(_api_key_header),
) -> str:
    """Dependency: validates X-API-Key and returns the key string for use in handler body."""
    return await require_api_key(api_key)
