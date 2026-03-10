"""FastAPI dependency injection helpers."""

from talent_graph.api.auth import require_api_key, require_api_key_returning

get_current_key = require_api_key_returning

__all__ = ["require_api_key", "get_current_key"]
