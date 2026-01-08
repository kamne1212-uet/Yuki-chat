import aiohttp
import json
from ai.prompts import SYSTEM_PROMPT

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "llama3:8b-instruct-q4_K_M"
MAX_TOKENS = 128


def build_prompt(messages: list[dict]) -> str:

    convo = SYSTEM_PROMPT.strip() + "\n\n"

    for m in messages:
        role = m["role"]
        content = m["content"]

        if role == "system":
            convo += f"{content}\n"
        else:
            convo += f"{role}: {content}\n"

    convo += "assistant:"
    return convo


async def stream_llm(messages: list[dict]):
    prompt = build_prompt(messages)

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": MAX_TOKENS
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(OLLAMA_URL, json=payload) as resp:
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


