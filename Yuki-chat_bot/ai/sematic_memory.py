import sqlite3
import json
import math
from datetime import datetime
from typing import List, Dict
import threading

_DB_LOCK = threading.Lock()


class SemanticMemory:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        with _DB_LOCK, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    # ---------- Vector utils ----------

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ---------- Core APIs ----------

    def add(
        self,
        user_id: str,
        content: str,
        embedding: List[float],
        source: str = "chat",
    ):
        with _DB_LOCK, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO semantic_memory
                (user_id, content, embedding, source, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    content,
                    json.dumps(embedding),
                    source,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()

    def search(
        self,
        user_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        min_score: float = 0.75,
        exclude_source: str = None,
    ) -> List[Dict]:
        with _DB_LOCK, self._connect() as conn:
            # Filter out assistant messages at SQL level for better performance
            if exclude_source:
                cur = conn.execute(
                    """
                    SELECT content, embedding, source
                    FROM semantic_memory
                    WHERE user_id = ? AND source != ?
                    """,
                    (user_id, exclude_source),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT content, embedding, source
                    FROM semantic_memory
                    WHERE user_id = ?
                    """,
                    (user_id,),
                )
            rows = cur.fetchall()

        scored = []
        for content, emb_json, source in rows:
            emb = json.loads(emb_json)
            score = self._cosine_similarity(query_embedding, emb)
            if score >= min_score:
                scored.append(
                    {
                        "content": content,
                        "score": score,
                        "source": source,
                    }
                )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

