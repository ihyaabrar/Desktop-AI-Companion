# Desktop AI Companion

> A Replika-style desktop companion that lives on your screen, remembers you, sees what you're doing, and can talk back.
> **Free, fully local by default. Bring-your-own API key for cloud upgrades.**

This repo is a monorepo containing:

- `apps/desktop/` — Tauri 2 + React + TypeScript shell (the always-on-top window, chat UI, sprite).
- `apps/sidecar/` — Python FastAPI sidecar that runs the LLM router, memory, vision and voice workers.
- `packages/prompts/` — versioned prompt templates.
- `docs/` — architecture and design docs. **Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).**

## Status

**M0 — Conversation Engine skeleton.** Hello-world chat: type a message, get a streamed reply from a local Ollama model (or an OpenAI/Anthropic key if configured). Everything else (memory, personality card, transparent always-on-top window, voice, screen vision, avatar) lands in later milestones.

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| **Node 20+** | Frontend / Tauri build | https://nodejs.org or use Volta/nvm |
| **Rust (stable)** | Tauri build | https://rustup.rs |
| **Python 3.11+** | Sidecar | https://python.org |
| **uv** | Fast Python package manager | https://docs.astral.sh/uv/ |
| **Ollama** *(default LLM provider)* | Local LLM runtime | https://ollama.com/download |

> Tauri 2 also needs platform-specific build tools — see https://tauri.app/start/prerequisites/.

After installing Ollama, pull the default models:

```bash
ollama pull qwen2.5:7b          # chat
ollama pull nomic-embed-text    # embeddings (used in M2)
```

If you'd rather use a cloud provider, leave Ollama out and copy `apps/sidecar/.env.example` to `apps/sidecar/.env` and set one of:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
```

…then set `LLM_MODEL=gpt-4o-mini` (or any [LiteLLM-supported model](https://docs.litellm.ai/docs/providers)).

## Setup

```bash
# 1. Sidecar (Python)
cd apps/sidecar
uv sync
cp .env.example .env            # edit if you want cloud keys

# 2. Desktop app (Node + Rust)
cd ../desktop
npm install
```

## Run (dev)

In two terminals:

```bash
# terminal 1 — sidecar
cd apps/sidecar
uv run uvicorn companion.main:app --host 127.0.0.1 --port 8765 --reload

# terminal 2 — desktop app
cd apps/desktop
npm run tauri:dev
```

Or, after M1 lands, `npm run tauri:dev` will spawn the sidecar automatically.

## Tests / lint

```bash
# Python
cd apps/sidecar && uv run ruff check . && uv run pytest

# Frontend
cd apps/desktop && npm run lint && npm run typecheck
```

## Roadmap

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §6.

| Milestone | Goal |
|---|---|
| **M0** *(this PR)* | Repo scaffolding + Tauri shell + Python sidecar + LiteLLM hello-world chat. |
| M1 | Personality / Companion Card. |
| M2 | Memory: episodic (Chroma) + semantic (SQLite) + extractor + retrieval. |
| M3 | Desktop Presence shell (always-on-top transparent window, draggable sprite). |
| M4 | Voice (faster-whisper STT + Piper/ElevenLabs TTS). |
| M5 | Screen Vision (opt-in, allowlisted, local moondream2 by default). |
| M6 | Avatar polish (Rive emotion states). |

## License

TBD.
