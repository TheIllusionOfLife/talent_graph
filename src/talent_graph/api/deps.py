"""FastAPI dependency injection helpers."""

from talent_graph.api.auth import (
    require_admin_key,
    require_api_key,
    require_api_key_returning,
    require_user_key,
)

get_current_key = require_api_key_returning

__all__ = ["require_api_key", "require_admin_key", "require_user_key", "get_current_key"]
