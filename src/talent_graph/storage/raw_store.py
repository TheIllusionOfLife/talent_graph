"""Raw JSON storage — saves API responses to disk before processing."""

import json
from datetime import UTC, datetime
from pathlib import Path

from talent_graph.config.settings import get_settings


class RawStore:
    def __init__(self, base_dir: str | None = None) -> None:
        self._base = Path(base_dir or get_settings().raw_data_dir)

    def save(self, source: str, entity_type: str, entity_id: str, data: dict) -> Path:
        """Persist raw API response. Returns path written."""
        directory = self._base / source / entity_type
        directory.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        path = directory / f"{entity_id}_{ts}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, source: str, entity_type: str, entity_id: str) -> dict | None:
        """Load the most recent raw file for an entity, or None if absent."""
        directory = self._base / source / entity_type
        if not directory.exists():
            return None
        matches = sorted(directory.glob(f"{entity_id}_*.json"), reverse=True)
        if not matches:
            return None
        return json.loads(matches[0].read_text(encoding="utf-8"))
