"""Episodic memory store backed by ChromaDB.

Stores short narrative snippets ("vivid moments worth remembering") as
embeddings. Recall = top-K nearest neighbours to a query string.

ChromaDB persists to `${DATA_DIR}/chroma`. The collection is created lazily on
first access and reset between tests via `reset_for_tests()`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from companion.memory.embeddings import get_embedder
from companion.settings import settings

_COLLECTION_NAME = "episodic"
_lock = Lock()
_client: ClientAPI | None = None
_collection: Collection | None = None


class _ChromaEmbeddingAdapter(EmbeddingFunction[Documents]):
    """Adapts our `Embedder` protocol into the shape Chroma expects."""

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def name() -> str:
        return "companion-embedder"

    def __call__(self, input: Documents) -> Embeddings:
        return get_embedder()(list(input))


def _get_collection() -> Collection:
    global _client, _collection
    with _lock:
        if _collection is not None:
            return _collection
        chroma_dir = Path(settings.data_dir).expanduser() / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(chroma_dir))
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=_ChromaEmbeddingAdapter(),
        )
        return _collection


def add(text: str, *, kind: str = "episode", extra_meta: dict[str, Any] | None = None) -> str:
    """Persist a single episodic memory and return its id."""
    if not text.strip():
        raise ValueError("episodic.add: text must be non-empty")
    coll = _get_collection()
    mem_id = str(uuid.uuid4())
    meta: dict[str, str] = {
        "kind": kind,
        "created_at": datetime.now(UTC).isoformat(),
    }
    if extra_meta:
        for k, v in extra_meta.items():
            meta[k] = str(v)
    coll.add(ids=[mem_id], documents=[text], metadatas=[meta])
    return mem_id


def query(text: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Return up to `top_k` memories most similar to `text`, newest-relevance first."""
    coll = _get_collection()
    if coll.count() == 0:
        return []
    n = min(top_k, coll.count())
    result = coll.query(query_texts=[text], n_results=n)
    out: list[dict[str, Any]] = []
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    ids = (result.get("ids") or [[]])[0]
    for i, doc in enumerate(docs):
        out.append(
            {
                "id": ids[i] if i < len(ids) else None,
                "text": doc,
                "metadata": metas[i] if i < len(metas) else {},
                "distance": distances[i] if i < len(distances) else None,
            }
        )
    return out


def list_all(limit: int = 100) -> list[dict[str, Any]]:
    """Return all stored memories (newest first), capped at `limit`."""
    coll = _get_collection()
    if coll.count() == 0:
        return []
    result = coll.get(limit=limit)
    out: list[dict[str, Any]] = []
    for i, doc in enumerate(result.get("documents") or []):
        out.append(
            {
                "id": (result.get("ids") or [])[i],
                "text": doc,
                "metadata": (result.get("metadatas") or [])[i] if result.get("metadatas") else {},
            }
        )
    out.sort(
        key=lambda m: m.get("metadata", {}).get("created_at", ""),
        reverse=True,
    )
    return out


def count() -> int:
    return _get_collection().count()


def clear() -> None:
    """Delete every memory. Used by `DELETE /memory/episodic` and tests."""
    global _client, _collection
    coll = _get_collection()
    existing = coll.get()
    ids = existing.get("ids") or []
    if ids:
        coll.delete(ids=ids)


def reset_for_tests() -> None:
    """Drop the cached client so the next call rebuilds against the fresh data_dir."""
    global _client, _collection
    with _lock:
        _client = None
        _collection = None
