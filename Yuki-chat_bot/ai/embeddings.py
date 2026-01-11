import requests

OLLAMA_URL = "http://ollama:11434/api/embeddings"
MODEL = "nomic-embed-text" # Embed model


def embed(text: str) -> list[float]:
    r = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": text,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["embedding"]


