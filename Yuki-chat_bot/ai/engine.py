import aiohttp
import json
from typing import AsyncGenerator, Optional

from ai.prompts import PERSONA_PROMPT

# ==============================
# Ollama config
# ==============================
OLLAMA_URL = "http://ollama:11434/api/generate"

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 300


# ==============================
# Models
# ==============================
ANSWER_MODEL = "llama3:8b-instruct-q4_K_M"
ANSWER_MAX_TOKENS = 256

SUMMARY_MODEL = "phi3:mini"
SUMMARY_MAX_TOKENS = 128

SUMMARY_CONVO_MODEL = "qwen2:1.5b"


# ==============================
# Core Ollama streamer
# ==============================
async def _stream_ollama(
    *,
    prompt: str,
    model: str,
    options: dict,
    keep_alive: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Low-level streaming wrapper for Ollama
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": options,
    }

    # Only attach keep_alive when explicitly requested
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive

    timeout = aiohttp.ClientTimeout(
        connect=CONNECT_TIMEOUT,
        total=READ_TIMEOUT,
    )

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(OLLAMA_URL, json=payload) as resp:
            resp.raise_for_status()

            async for raw in resp.content:
                if not raw:
                    continue

                try:
                    data = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                token = data.get("response")
                if token:
                    yield token


# ==============================
# Answer generation
# ==============================
def build_answer_prompt(messages: list[dict]) -> str:
    """
    Build prompt for main Yuki response
    """
    convo = PERSONA_PROMPT.strip() + "\n\n"

    for m in messages[-10:]:
        role = m["role"]
        content = m["content"]

        if role == "system":
            convo += f"{content}\n"
        else:
            convo += f"{role}: {content}\n"

    convo += "Yuki:"
    return convo


async def stream_llm(messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    Stream main answer from Yuki (always warm)
    """
    prompt = build_answer_prompt(messages)

    async for token in _stream_ollama(
        prompt=prompt,
        model=ANSWER_MODEL,
        options={
            "num_predict": ANSWER_MAX_TOKENS,
        },
        keep_alive="10m",   # always keep main model warm in 10 minutes without any request
    ):
        yield token


# ==============================
# Answer summary (short-term memory)
# ==============================
def build_answer_summary_prompt(full_answer: str) -> str:
    return (
        "You summarize Yuki's reply for memory.\n"
        "Rules:\n"
        "- Yuki is a girl\n"
        "- 1 sentence, max 25 words\n"
        "- third-person\n"
        "- factual\n"
        "- no tone, no examples\n"
        "- refer to Yuki by name\n\n"
        f"Yuki: {full_answer}\n"
        "Summary:"
    )


async def stream_answer_summary_llm(
    full_answer: str
) -> AsyncGenerator[str, None]:
    """
    Summarize Yuki's answer (warm briefly)
    """
    prompt = build_answer_summary_prompt(full_answer)

    async for token in _stream_ollama(
        prompt=prompt,
        model=SUMMARY_MODEL,
        options={
            "num_predict": SUMMARY_MAX_TOKENS,
            "temperature": 0.2,
            "repeat_penalty": 1.1,
        },
        keep_alive="3m",   # short warm only
    ):
        yield token


# ==============================
# Conversation summary (long-term memory)
# ==============================
def build_convo_summary_prompt(messages: list[dict]) -> str:
    prompt = (
        "Summarize the conversation between Yuki and the user.\n"
        "Rules:\n"
        "- Yuki is a girl\n"
        "- 2–3 sentences\n"
        "- third-person\n"
        "- factual\n"
        "- no dialogue\n"
        "- do not roleplay\n\n"
    )

    for m in messages:
        prompt += f"{m['role']}: {m['content']}\n"

    prompt += "Summary:"
    return prompt


async def stream_convo_summary_llm(
    messages: list[dict]
) -> AsyncGenerator[str, None]:
    """
    Summarize long conversation.
    No keep_alive – model unloads after use
    """
    prompt = build_convo_summary_prompt(messages)

    async for token in _stream_ollama(
        prompt=prompt,
        model=SUMMARY_CONVO_MODEL,
        options={
            "num_predict": SUMMARY_MAX_TOKENS,
            "temperature": 0.2,
        },
        keep_alive=None,   # do NOT keep warm
    ):
        yield token


