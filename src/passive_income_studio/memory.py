from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MemoryRecord:
    id: int
    content: str
    user_id: str
    tags: list[str]
    metadata: dict[str, Any]
    score: float
    created_at: float


class LocalMemory:
    """Small OpenMemory-shaped local memory store.

    OpenMemory examples expose `add`, `search`, `history`, and `delete`.
    This keeps that shape while avoiding a server, Docker, or embedding spend
    in v1. Search uses lightweight lexical scoring over local SQLite.
    """

    def __init__(self, path: Path | str = "data/memory.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at)")
            conn.commit()

    async def add(
        self,
        content: str,
        user_id: str = "default",
        meta: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> int:
        return self.add_sync(content, user_id=user_id, meta=meta, tags=tags)

    def add_sync(
        self,
        content: str,
        user_id: str = "default",
        meta: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO memories (user_id, content, tags_json, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    content,
                    json.dumps(tags or []),
                    json.dumps(meta or {}, sort_keys=True),
                    time.time(),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    async def search(self, query: str, user_id: str = "default", limit: int = 5) -> list[dict[str, Any]]:
        return [record_to_dict(record) for record in self.search_sync(query, user_id=user_id, limit=limit)]

    def search_sync(self, query: str, user_id: str = "default", limit: int = 5) -> list[MemoryRecord]:
        terms = tokenize(query)
        if not terms:
            return []
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
                (user_id,),
            ).fetchall()

        scored: list[MemoryRecord] = []
        for row in rows:
            haystack = " ".join(
                [
                    row["content"],
                    " ".join(json.loads(row["tags_json"])),
                    json.dumps(json.loads(row["metadata_json"]), sort_keys=True),
                ]
            ).lower()
            score = sum(1.0 for term in terms if term in haystack)
            if score <= 0:
                continue
            age_days = max((time.time() - float(row["created_at"])) / 86400, 0)
            recency = 1 / (1 + age_days)
            scored.append(row_to_record(row, score + recency * 0.25))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def history(self, user_id: str = "default", limit: int = 5) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [record_to_dict(row_to_record(row, score=1.0)) for row in rows]

    async def delete(self, memory_id: int) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()


class OpenMemoryBridge:
    """Optional bridge to `openmemory-py` when the full SDK is installed."""

    def __init__(self) -> None:
        try:
            from openmemory.client import Memory
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("openmemory-py is not installed; use LocalMemory instead.") from exc
        self.memory = Memory()


def tokenize(value: str) -> list[str]:
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return [token for token in normalized.split() if len(token) > 2]


def row_to_record(row: sqlite3.Row, score: float) -> MemoryRecord:
    return MemoryRecord(
        id=int(row["id"]),
        content=str(row["content"]),
        user_id=str(row["user_id"]),
        tags=json.loads(row["tags_json"]),
        metadata=json.loads(row["metadata_json"]),
        score=score,
        created_at=float(row["created_at"]),
    )


def record_to_dict(record: MemoryRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "content": record.content,
        "user_id": record.user_id,
        "tags": record.tags,
        "metadata": record.metadata,
        "score": record.score,
        "created_at": record.created_at,
    }

