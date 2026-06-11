from __future__ import annotations

import hashlib
import json
from pathlib import Path


class HistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._items: set[str] | None = None

    def load(self) -> set[str]:
        if self._items is not None:
            return self._items
        if not self.path.exists():
            self._items = set()
            return self._items
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._items = set()
            return self._items
        self._items = {str(item) for item in data if isinstance(item, str)}
        return self._items

    def add(self, item: str) -> None:
        self.load().add(item)

    def contains(self, item: str) -> bool:
        return item in self.load()

    def save(self) -> None:
        items = sorted(self.load())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items, indent=2), encoding="utf-8")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slide_id(digest: str, slide_index: int) -> str:
    return f"{digest}::{slide_index}"

