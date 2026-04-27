# Companion sidecar

FastAPI service that exposes the LLM router, memory, vision and voice workers to the Tauri shell over local HTTP.

```bash
uv sync
cp .env.example .env
uv run uvicorn companion.main:app --host 127.0.0.1 --port 8765 --reload
```

Endpoints in M0:

- `GET  /health` — liveness probe used by the Tauri shell on startup.
- `POST /chat` — server-sent events stream of `{type: "token"|"done", ...}`.

See [`../../docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) §3 for the full contract.
