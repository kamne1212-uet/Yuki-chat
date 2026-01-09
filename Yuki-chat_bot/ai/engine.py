import aiohttp
import json
import asyncio
from ai.prompts import SYSTEM_PROMPT

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "llama3:8b-instruct-q4_K_M"
MAX_TOKENS = 256

# Timeout configuration (in seconds)
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 300  # 5 minutes for streaming responses


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

    timeout = aiohttp.ClientTimeout(
        connect=CONNECT_TIMEOUT,
        total=READ_TIMEOUT
    )

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(OLLAMA_URL, json=payload) as resp:
                    resp.raise_for_status()  # Raise exception for bad status codes
                    
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
                            
            except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                # Handle timeout/cancellation gracefully
                print(f"Stream timeout/cancellation: {e}")
                return
            except aiohttp.ClientError as e:
                # Handle HTTP client errors
                print(f"HTTP client error: {e}")
                return
                
    except (asyncio.TimeoutError, asyncio.CancelledError) as e:
        # Handle session-level timeout/cancellation
        print(f"Session timeout/cancellation: {e}")
        return
    except Exception as e:
        # Handle any other unexpected errors
        print(f"Unexpected error in stream_llm: {e}")
        return


