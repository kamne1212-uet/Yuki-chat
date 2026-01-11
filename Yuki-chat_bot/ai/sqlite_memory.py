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
            # Check if summaries table exists and what schema it has
            cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='summaries'")
            schema_result = cur.fetchone()
            
            if schema_result:
                schema_sql = schema_result[0]
                # Check if old schema (user_id as PRIMARY KEY)
                if 'user_id TEXT PRIMARY KEY' in schema_sql:
                    # Old schema detected, migrate data
                    try:
                        cur.execute("SELECT user_id, summary, updated_at FROM summaries")
                        old_data = cur.fetchall()
                        if old_data:
                            # Create new table with new schema
                            cur.execute(
                                """
                                CREATE TABLE summaries_new (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id TEXT NOT NULL,
                                    summary TEXT NOT NULL,
                                    created_at TEXT NOT NULL
                                )
                                """
                            )
                            cur.execute(
                                """
                                CREATE INDEX idx_summaries_user_created 
                                ON summaries_new(user_id, created_at DESC)
                                """
                            )
                            # Migrate data - split accumulated summaries by newline
                            for user_id, summary, updated_at in old_data:
                                if summary:
                                    # Split by newline to get individual summaries
                                    summaries = [s.strip() for s in summary.split('\n') if s.strip()]
                                    # Keep only the 2 most recent (last 2 in the list)
                                    summaries = summaries[-2:] if len(summaries) > 2 else summaries
                                    for s in summaries:
                                        cur.execute(
                                            "INSERT INTO summaries_new (user_id, summary, created_at) VALUES (?, ?, ?)",
                                            (user_id, s, updated_at or datetime.utcnow().isoformat())
                                        )
                            # Replace old table with new
                            cur.execute("DROP TABLE summaries")
                            cur.execute("ALTER TABLE summaries_new RENAME TO summaries")
                    except Exception:
                        pass  # Migration failed, will use new schema
                else:
                    # New schema already exists, just ensure index exists
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_summaries_user_created 
                        ON summaries(user_id, created_at DESC)
                        """
                    )
            else:
                # Table doesn't exist, create new schema
                cur.execute(
                    """
                    CREATE TABLE summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX idx_summaries_user_created 
                    ON summaries(user_id, created_at DESC)
                    """
                )
            conn.commit()

    # ===== Message APIs =====

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

    # ===== Summary APIs =====

    def get_summary(self, user_id: str, limit: int = 2) -> Optional[str]:
        """
        Get the most recent summaries for a user (default: 2 most recent).
        Returns combined summaries separated by newlines.
        """
        with _DB_LOCK, self._connect() as conn:
            cur = conn.execute(
                """
                SELECT summary FROM summaries 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (user_id, limit),
            )
            rows = cur.fetchall()
            if not rows:
                return None
            # Combine summaries (most recent first)
            summaries = [row[0] for row in rows]
            # Reverse to show older first, then newer
            return "\n".join(reversed(summaries))

    def upsert_summary(self, user_id: str, summary: str, keep_recent: int = 2):
        """
        Add a new summary and keep only the most recent N summaries (default: 2).
        Old summaries beyond the limit will be automatically deleted.
        """
        with _DB_LOCK, self._connect() as conn:
            # Insert new summary
            conn.execute(
                """
                INSERT INTO summaries (user_id, summary, created_at)
                VALUES (?, ?, ?)
                """,
                (user_id, summary, datetime.utcnow().isoformat()),
            )
            
            # Delete old summaries beyond the limit
            # Get IDs of summaries to keep (most recent N)
            cur = conn.execute(
                """
                SELECT id FROM summaries 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (user_id, keep_recent),
            )
            keep_ids = {row[0] for row in cur.fetchall()}
            
            # Delete summaries not in keep_ids
            if keep_ids:
                placeholders = ','.join('?' * len(keep_ids))
                conn.execute(
                    f"""
                    DELETE FROM summaries 
                    WHERE user_id = ? AND id NOT IN ({placeholders})
                    """,
                    (user_id, *keep_ids),
                )
            else:
                # If no summaries to keep, delete all (shouldn't happen, but safety check)
                conn.execute(
                    "DELETE FROM summaries WHERE user_id = ?",
                    (user_id,),
                )
            
            conn.commit()

    # ===== Prompt Helper =====

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



