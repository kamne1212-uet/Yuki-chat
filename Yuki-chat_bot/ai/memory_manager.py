from ai.sqlite_memory import SQLiteMemory
from ai.sematic_memory import SemanticMemory
from ai.embeddings import embed

# ===== MEMORY MANAGER =====
class MemoryManager:
    def __init__(self, db_path: str):
        self.raw = SQLiteMemory(db_path)
        self.semantic = SemanticMemory(db_path)

    def add_user_message(self, user_id: str, content: str):
        self.raw.add_message(user_id, "user", content)

        # Try to add to semantic memory, but don't fail if embedding service is unavailable
        try:
            emb = embed(content)
            self.semantic.add(user_id, content, emb, source="user")
        except Exception as e:
            # Log error but continue - semantic search is optional
            print(f"Warning: Failed to add semantic memory for user {user_id}: {e}")

    async def add_Yuki_message(
        self,
        user_id: str,
        full_content: str,
        summarize_llm_func,
):
       """
       Store summarized Yuki message instead of full content
       """

       summary_text = ""

       try:
          async for chunk in summarize_llm_func(full_content):
            if chunk:
                summary_text += chunk
       except Exception as e:
            print(f"Warning: Yuki summary failed: {e}")

       summary_text = summary_text.strip()

       # fallback
       if not summary_text:
            summary_text = full_content[:200]

       self.raw.add_message(user_id, "Yuki", summary_text)



    def build_context(
        self,
        user_id: str,
        system_prompt: str,
        query: str,
        window: int = 8
    ):
        # Enhanced system prompt with anti-repetition instruction
        enhanced_prompt = f"{system_prompt}\n\nDo not repeat your previous responses verbatim."
        messages = [{"role": "system", "content": enhanced_prompt}]

        # Add conversation summary if available (provides overview of past conversations)
        summary = self.raw.get_summary(user_id)
        if summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"Previous conversation context: {summary}\n\nNote: This summary describes past conversations. 'The user' refers to the person you're talking to, and Yuki refers to your previous responses.",
                }
            )
            # Reduce window when summary exists - summary already covers past context
            # This optimizes token usage while maintaining recent context
            # Reduce by 2 messages, but keep at least 6 for immediate context
            window = max(6, window - 2)

        # semantic recall - exclude Yuki messages at SQL level for better performance
        try:
            q_emb = embed(query)
            memories = self.semantic.search(user_id, q_emb, exclude_source="Yuki")
        except Exception as e:
            # If embedding fails, skip semantic search but continue with conversation
            print(f"Warning: Semantic search failed for user {user_id}: {e}")
            memories = []

        # Get recent messages with smart filtering
        recent_messages = self._get_smart_recent_messages(user_id, window)
        recent_contents = {msg["content"] for msg in recent_messages}

        # Filter out memories that are already in recent messages to avoid duplication
        unique_memories = [
            m for m in memories 
            if m["content"] not in recent_contents
        ]

        if unique_memories:
            joined = "\n".join(
                f"- {m['content']}" for m in unique_memories
            )
            messages.append(
                {
                    "role": "system",
                    "content": "Relevant past memories:\n" + joined,
                }
            )

        messages.extend(recent_messages)
        return messages

    def _get_smart_recent_messages(self, user_id: str, window: int = 8, max_Yuki: int = 2):
        """
        Get recent messages with smart filtering:
        - Keep all user messages (they provide context)
        - Keep only the most recent 1-2 Yuki messages (reduces repetition)
        - Maintain chronological order
        - This reduces repetition risk while maintaining conversation flow
        """
        # Get more messages than needed to have options for filtering
        all_recent = self.raw.get_recent_messages(user_id, limit=window * 2)
        
        if not all_recent:
            return []
        
        # Separate user and Yuki messages (already in chronological order)
        user_messages = [msg for msg in all_recent if msg["role"] == "user"]
        Yuki_messages = [msg for msg in all_recent if msg["role"] == "Yuki"]
        
        # Keep only the most recent Yuki messages (max 2 for context)
        # Take from the end (most recent)
        recent_Yuki = Yuki_messages[-max_Yuki:] if len(Yuki_messages) > max_Yuki else Yuki_messages
        
        # Create sets of content to track which messages to keep
        # Use tuple (role, content) as key since content should be unique
        keep_user = {(msg["role"], msg["content"]) for msg in user_messages}
        keep_Yuki = {(msg["role"], msg["content"]) for msg in recent_Yuki}
        
        # Reconstruct conversation in chronological order
        result = []
        for msg in all_recent:
            msg_key = (msg["role"], msg["content"])
            if msg["role"] == "user" and msg_key in keep_user:
                result.append(msg)
            elif msg["role"] == "Yuki" and msg_key in keep_Yuki:
                result.append(msg)
        
        # Limit to window size (keep most recent)
        return result[-window:] if len(result) > window else result

    def update_summary(self, user_id: str, summary: str):
        """Update the conversation summary for a user"""
        self.raw.upsert_summary(user_id, summary)

    def get_summary(self, user_id: str):
        """Get the conversation summary for a user"""
        return self.raw.get_summary(user_id)

    def count_messages(self, user_id: str) -> int:
        """Get the total number of messages for a user"""
        return self.raw.count_messages(user_id)

    def should_summarize(self, user_id: str, threshold: int = 20) -> bool:
        """Check if conversation is long enough to benefit from summarization"""
        return self.count_messages(user_id) >= threshold

    async def generate_summary_async(self, user_id: str, stream_convo_summary_llm):
       """
       Generate long-term conversation summary
       """

       all_messages = self.raw.get_recent_messages(user_id, limit=50)
       if len(all_messages) < 10:
           return

       filtered = [
          {"role": m["role"], "content": m["content"]}
          for m in all_messages if m["role"] in ("user", "Yuki")
    ]

       summary_text = ""
       async for chunk in stream_convo_summary_llm(filtered):
           if chunk and chunk.strip():
                summary_text += chunk

       summary_text = summary_text.strip()
       if summary_text:
           self.raw.upsert_summary(user_id, summary_text, keep_recent=2)


