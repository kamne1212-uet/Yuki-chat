"""
SQLite Memory Module for Discord / Chatbot projects
Plug-and-play, no external dependencies
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Dict, Optional

_DB_LOCK = threading.Lock()


class SQLiteMemory:
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with _DB_LOCK, self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    user_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    # ---------- Message APIs ----------

    def add_message(self, user_id: str, role: str, content: str):
        with _DB_LOCK, self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, role, content, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def get_recent_messages(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        with _DB_LOCK, self._connect() as conn:
            cur = conn.execute(
                """
                SELECT role, content FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()

        return [
            {"role": role, "content": content}
            for role, content in reversed(rows)
        ]

    def count_messages(self, user_id: str) -> int:
        with _DB_LOCK, self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE user_id = ?",
                (user_id,),
            )
            return cur.fetchone()[0]

    def clear_messages(self, user_id: str):
        with _DB_LOCK, self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            conn.commit()

    # ---------- Summary APIs ----------

    def get_summary(self, user_id: str) -> Optional[str]:
        with _DB_LOCK, self._connect() as conn:
            cur = conn.execute(
                "SELECT summary FROM summaries WHERE user_id = ?",
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def upsert_summary(self, user_id: str, summary: str):
        with _DB_LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO summaries (user_id, summary, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET summary = excluded.summary,
                              updated_at = excluded.updated_at
                """,
                (user_id, summary, datetime.utcnow().isoformat()),
            )
            conn.commit()

    # ---------- Prompt Helper ----------

    def build_context(
        self,
        user_id: str,
        system_prompt: str,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Returns messages ready to send to LLM
        [system] + [summary?] + recent messages
        """
        messages = [{"role": "system", "content": system_prompt}]

        summary = self.get_summary(user_id)
        if summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"Conversation summary so far: {summary}",
                }
            )

        messages.extend(self.get_recent_messages(user_id, limit))
        return messages
