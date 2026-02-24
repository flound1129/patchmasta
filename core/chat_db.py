from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    backend TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    wav_path TEXT,
    tool_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class ChatHistoryDB:
    """Persistent SQLite store for AI chat conversations."""

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = (
                Path.home() / ".local" / "share" / "patchmasta" / "chat_history.db"
            )
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def add_conversation(self, backend: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO conversations (backend) VALUES (?)", (backend,)
        )
        self._conn.commit()
        return cur.lastrowid

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        wav_path: str | None = None,
        tool_name: str | None = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO messages (conversation_id, role, content, wav_path, tool_name)"
            " VALUES (?, ?, ?, ?, ?)",
            (conversation_id, role, content, wav_path, tool_name),
        )
        self._conn.commit()
        return cur.lastrowid

    def close(self) -> None:
        self._conn.close()
