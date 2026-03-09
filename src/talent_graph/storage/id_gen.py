"""ULID-based ID generation for all entities."""

from ulid import ULID


def new_id() -> str:
    """Return a new ULID string (sortable, URL-safe, collision-free)."""
    return str(ULID())
