"""Raw JSON storage — saves API responses to disk before processing."""

import glob as glob_module
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from talent_graph.config.settings import get_settings


def _safe_entity_id(entity_id: str) -> str:
    """Strip path-unsafe characters from entity_id to prevent path traversal."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", entity_id)


class RawStore:
    def __init__(self, base_dir: str | None = None) -> None:
        self._base = Path(base_dir or get_settings().raw_data_dir)

    def save(self, source: str, entity_type: str, entity_id: str, data: dict) -> Path:
        """Persist raw API response. Returns path written."""
        safe_id = _safe_entity_id(entity_id)
        directory = self._base / source / entity_type
        directory.mkdir(parents=True, exist_ok=True)
        # %f adds microseconds to prevent same-second collisions
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
        path = directory / f"{safe_id}_{ts}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, source: str, entity_type: str, entity_id: str) -> dict | None:
        """Load the most recent raw file for an entity, or None if absent."""
        safe_id = _safe_entity_id(entity_id)
        directory = self._base / source / entity_type
        if not directory.exists():
            return None
        pattern = str(directory / f"{glob_module.escape(safe_id)}_*.json")
        matches = sorted(Path(p) for p in glob_module.glob(pattern))
        if not matches:
            return None
        return cast("dict[Any, Any]", json.loads(matches[-1].read_text(encoding="utf-8")))
