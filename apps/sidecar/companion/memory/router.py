"""Debug HTTP routes for inspecting memory state."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from companion.memory import episodic, semantic
from companion.settings import settings

router = APIRouter(prefix="/memory", tags=["memory"])


class MemorySummary(BaseModel):
    semantic_count: int
    episodic_count: int


class SemanticUpsertBody(BaseModel):
    key: str = Field(..., min_length=1, max_length=120)
    value: Any
    evidence: str | None = None


@router.get("/summary", response_model=MemorySummary)
def memory_summary() -> MemorySummary:
    return MemorySummary(
        semantic_count=semantic.count(),
        episodic_count=episodic.count(),
    )


@router.get("/semantic", response_model=list[semantic.SemanticFact])
def list_semantic() -> list[semantic.SemanticFact]:
    return semantic.all_facts()


@router.put("/semantic", response_model=semantic.SemanticFact)
def upsert_semantic(body: SemanticUpsertBody) -> semantic.SemanticFact:
    try:
        return semantic.upsert(body.key, body.value, body.evidence)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/semantic/{key}", status_code=204)
def delete_semantic(key: str) -> None:
    semantic.delete(key)


@router.get("/episodic")
def list_episodic(limit: int = 50) -> list[dict[str, Any]]:
    return episodic.list_all(limit=limit)


@router.post("/episodic", response_model=dict)
def add_episodic(body: dict[str, Any]) -> dict[str, str]:
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=422, detail="text must be a non-empty string")
    extra = body.get("metadata") if isinstance(body.get("metadata"), dict) else None
    mem_id = episodic.add(text.strip(), extra_meta=extra)
    return {"id": mem_id}


@router.post("/episodic/query")
def query_episodic(body: dict[str, Any]) -> list[dict[str, Any]]:
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=422, detail="text must be a non-empty string")
    raw_top_k = body.get("top_k")
    top_k = settings.episodic_top_k if raw_top_k is None else raw_top_k
    return episodic.query(text.strip(), top_k=int(top_k))


@router.delete("/episodic", status_code=204)
def clear_episodic() -> None:
    episodic.clear()
