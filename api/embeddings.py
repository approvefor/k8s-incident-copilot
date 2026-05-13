from __future__ import annotations

import hashlib
import json
import os
import urllib.request


EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local_hash").lower()
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def embedding_dimensions() -> int:
    if "EMBEDDING_DIMENSIONS" in os.environ:
        return int(os.environ["EMBEDDING_DIMENSIONS"])
    if EMBEDDING_PROVIDER == "openai":
        return 1536
    return 64


def embed_text(text: str) -> list[float]:
    if EMBEDDING_PROVIDER == "openai":
        return embed_openai(text)
    return embed_local_hash(text, dimensions=embedding_dimensions())


def embed_local_hash(text: str, *, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.lower().encode("utf-8")).digest()
    values = (list(digest) * ((dimensions // len(digest)) + 1))[:dimensions]
    return [((value / 255.0) * 2.0) - 1.0 for value in values]


def embed_openai(text: str) -> list[float]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")

    payload = {
        "model": OPENAI_EMBEDDING_MODEL,
        "input": text,
    }
    if "EMBEDDING_DIMENSIONS" in os.environ:
        payload["dimensions"] = embedding_dimensions()

    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        body = json.loads(response.read().decode("utf-8"))
    return [float(value) for value in body["data"][0]["embedding"]]
