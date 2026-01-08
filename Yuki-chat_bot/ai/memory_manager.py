from ai.sqlite_memory import SQLiteMemory
from ai.sematic_memory import SemanticMemory
from ai.embeddings import embed

class MemoryManager:
    def __init__(self, db_path: str):
        self.raw = SQLiteMemory(db_path)
        self.semantic = SemanticMemory(db_path)

    def add_user_message(self, user_id: str, content: str):
        self.raw.add_message(user_id, "user", content)

        emb = embed(content)
        self.semantic.add(user_id, content, emb, source="user")

    def add_assistant_message(self, user_id: str, content: str):
        self.raw.add_message(user_id, "assistant", content)

        emb = embed(content)
        self.semantic.add(user_id, content, emb, source="assistant")

    def build_context(
        self,
        user_id: str,
        system_prompt: str,
        query: str,
        window: int = 8,
    ):
        messages = [{"role": "system", "content": system_prompt}]

        # semantic recall
        q_emb = embed(query)
        memories = self.semantic.search(user_id, q_emb)

        if memories:
            joined = "\n".join(
                f"- {m['content']}" for m in memories
            )
            messages.append(
                {
                    "role": "system",
                    "content": "Relevant past memories:\n" + joined,
                }
            )

        messages.extend(self.raw.get_recent_messages(user_id, window))
        return messages
