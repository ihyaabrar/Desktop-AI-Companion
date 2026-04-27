"""Embedding functions for the memory store.

Two implementations:
* `OllamaEmbedder` — production default, calls a local Ollama server's
  `/api/embeddings` with `nomic-embed-text`.
* `FakeHashEmbedder` — deterministic hash-based fallback used in tests so they
  don't need a running Ollama instance. Quality is terrible but the SHAPE is
  identical, which is what the rest of the code cares about.

Chroma calls the embedding function with a list of strings; we always return a
list of fixed-length float vectors.
"""

from __future__ import annotations

import hashlib
import struct
from typing import Protocol

import httpx

from companion.settings import settings


class Embedder(Protocol):
    """Anything that turns a list of texts into a list of equally-sized vectors."""

    dimension: int

    def __call__(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder:
    """Embeds via Ollama. Uses the model named in `settings.embedding_model`."""

    dimension: int = 768  # nomic-embed-text default

    def __call__(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        with httpx.Client(timeout=30.0) as client:
            for text in texts:
                resp = client.post(
                    f"{settings.ollama_api_base}/api/embeddings",
                    json={"model": settings.embedding_model, "prompt": text},
                )
                resp.raise_for_status()
                out.append(resp.json()["embedding"])
        return out


class FakeHashEmbedder:
    """Deterministic embedder for tests. Hashes the text into a 32-d float vector."""

    dimension: int = 32

    def __call__(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            # 32 bytes -> 8 floats (4 bytes each). Repeat 4x to reach 32 dims.
            base = list(struct.unpack("8f", digest))
            vec = base * (self.dimension // len(base))
            out.append(vec[: self.dimension])
        return out


_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the singleton embedder. Tests should call `set_embedder` first."""
    global _embedder
    if _embedder is None:
        _embedder = OllamaEmbedder()
    return _embedder


def set_embedder(embedder: Embedder | None) -> None:
    """Override the embedder. Pass None to reset to default."""
    global _embedder
    _embedder = embedder
