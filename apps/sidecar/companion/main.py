"""FastAPI entry point for the Companion sidecar."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from companion import __version__
from companion.conversation.engine import stream_reply
from companion.personality.router import router as personality_router
from companion.settings import settings

app = FastAPI(title="Companion sidecar", version=__version__)

# Allow the Tauri WebView (which loads from a tauri:// or http://localhost origin) to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(personality_router)


class ChatRequest(BaseModel):
    """Body for `POST /chat`."""

    user_message: str = Field(..., min_length=1)
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, model=settings.llm_model)


@app.post("/chat")
async def chat(req: ChatRequest) -> EventSourceResponse:
    """Stream the assistant reply as Server-Sent Events.

    Event shapes (each event's `data` is JSON):
      - {"type": "token", "text": "..."}            — partial token
      - {"type": "done", "session_id": "..."}        — terminal marker
      - {"type": "error", "message": "..."}          — fatal error during stream
    """

    async def gen() -> AsyncIterator[dict[str, str]]:
        try:
            async for token in stream_reply(req.session_id, req.user_message):
                yield {"data": json.dumps({"type": "token", "text": token})}
        except Exception as exc:
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}
            return
        yield {"data": json.dumps({"type": "done", "session_id": req.session_id})}

    return EventSourceResponse(gen())
