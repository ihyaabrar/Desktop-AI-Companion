# Desktop AI Companion — Architecture & Build Plan

> **Status:** Draft v0.1 — for review.
> **Goal:** A Replika-style desktop companion that lives on your screen, remembers you, sees what you're doing, and can talk back.
> **Scope reference:** 6 modules — Conversation, Memory, Personality, Interaction (Chat→Voice→Avatar), Screen Vision, Desktop Presence.

---

## 0. TL;DR — Recommended Stack

| Layer | Recommendation | Why |
|---|---|---|
| Shell | **Tauri 2.x** (Rust + WebView) | Tiny binary, native always-on-top window, transparent + non-focusable supported, cross-platform. |
| Frontend | **React + TypeScript + Vite** in Tauri WebView | Familiar, fast iteration for chat UI + companion-card form. |
| Backend runtime | **Python sidecar** spawned by Tauri | LiteLLM, Chroma, Whisper, all have first-class Python support. Rust ecosystem isn't there yet. |
| IPC | **Tauri Commands + local HTTP (FastAPI on 127.0.0.1:random_port)** | Streaming SSE for tokens, simple to debug, language-agnostic. |
| LLM router | **LiteLLM** | As specified. Lets us swap OpenAI ↔ Ollama ↔ Anthropic without code changes. |
| Vector store | **Chroma** (embedded mode, persistent) | As specified. No server to manage. |
| Structured store | **SQLite** via `sqlite3` / `sqlmodel` | As specified. Single-file DB lives next to user data. |
| STT | **faster-whisper** (local, CTranslate2) with OpenAI Whisper API fallback | Local default = privacy + no cost; API for low-end machines. |
| TTS | **ElevenLabs API** primary, **Piper** local fallback | ElevenLabs sounds dramatically better; Piper for offline mode. |
| Avatar (phase 1) | **Rive** 2D for desktop sprite | Lightweight, animated, emotion states, runs in WebView. |
| Avatar (phase 2) | **Ready Player Me** 3D in `<model-viewer>` or three.js | Mid-fidelity, free, web-friendly. |
| Avatar (phase 3, optional) | **MetaHuman** | **Recommend dropping** — see §7 Risks. |
| Screen capture | **mss** (Python) or Tauri Rust `screenshots` crate | Cross-platform, fast. |
| Vision LLM | **GPT-4o-mini Vision** default, **moondream2** local option | Cheap and accurate; local for privacy mode. |

**Build order I recommend** (different from the scope's literal order — see §6):
**M0** Chat MVP → **M1** Personality + Companion Card → **M2** Memory (episodic + semantic) → **M3** Desktop Presence shell → **M4** Voice → **M5** Screen Vision → **M6** Avatar polish.

---

## 1. System Data Flow

```
                ┌──────────────────────────────────────────────┐
                │              TAURI WINDOW (always-on-top)    │
                │  ┌──────────────┐         ┌──────────────┐  │
                │  │  Sprite      │         │  Chat Panel  │  │
                │  │  (Rive)      │◀───────▶│  (React)     │  │
                │  └──────────────┘  emit   └──────┬───────┘  │
                │           ▲          state       │          │
                └───────────┼─────────────────────┼───────────┘
                            │ IPC (Tauri cmd)     │ HTTP/SSE
                            ▼                     ▼
              ┌─────────────────────────────────────────────────┐
              │       PYTHON SIDECAR (FastAPI on 127.0.0.1)     │
              │                                                  │
              │  ┌────────────────────────────────────────────┐ │
              │  │           Conversation Engine              │ │
              │  │  ┌──────────────┐   ┌──────────────────┐  │ │
              │  │  │ Context       │──▶│   LiteLLM       │  │ │
              │  │  │ Builder       │   │   (router)      │  │ │
              │  │  └──────┬───────┘   └────────┬─────────┘  │ │
              │  │         │                    │            │ │
              │  └─────────┼────────────────────┼────────────┘ │
              │            │ inject             │ stream tokens│
              │   ┌────────▼────────┐  ┌────────▼─────────┐    │
              │   │  Personality    │  │   Extractor      │    │
              │   │  (system prompt │  │   (post-turn,    │    │
              │   │   compiler)     │  │    LLM call)     │    │
              │   └────────┬────────┘  └────────┬─────────┘    │
              │            │                    │              │
              │   ┌────────▼────────────────────▼───────────┐  │
              │   │              Memory System              │  │
              │   │  ┌─────────────┐   ┌─────────────────┐  │  │
              │   │  │  Chroma     │   │   SQLite        │  │  │
              │   │  │ (episodic   │   │  (semantic:     │  │  │
              │   │  │  vectors)   │   │   profile,      │  │  │
              │   │  │             │   │   prefs, card)  │  │  │
              │   │  └─────────────┘   └─────────────────┘  │  │
              │   └──────────────────▲──────────────────────┘  │
              │                      │                          │
              │   ┌──────────────────┴────────────────────────┐ │
              │   │            Screen Vision Worker            │ │
              │   │  capture(N s) → vision LLM → context note │ │
              │   └────────────────────────────────────────────┘ │
              │                                                  │
              │   ┌────────────────────────────────────────────┐ │
              │   │         Voice Worker (optional)            │ │
              │   │  mic → Whisper → text   |   text → TTS    │ │
              │   └────────────────────────────────────────────┘ │
              └──────────────────────────────────────────────────┘
```

**Key flows:**

1. **Chat turn (sync path):** UI → `POST /chat` (user message) → Context Builder pulls (a) personality prompt, (b) recent N turns, (c) top-K episodic memories, (d) all semantic profile facts, (e) latest screen-vision note → LiteLLM → SSE stream tokens back to UI.
2. **Memory write (async path):** After response finishes, Extractor runs in background on the (user_msg, assistant_msg) pair → emits 0..N "facts" → router decides episodic vs semantic → writes.
3. **Screen vision (independent loop):** Background worker, runs only when enabled, writes latest "what user is doing" note to a single-row table that Context Builder reads.
4. **Emotion → sprite:** Conversation Engine tags assistant response with an emotion (happy/sad/curious/…) → emits Tauri event → Rive sprite swaps animation state.

---

## 2. Decisions That Need to Be Made (Before Coding)

These are the 6 forks I flagged. Each has my recommendation + rationale + tradeoff. **You can override any of them — that's the point of writing this down before scaffolding.**

### D1. Backend location: Python sidecar vs Rust-native

| Option | Pros | Cons |
|---|---|---|
| **A. Python sidecar (recommended)** | LiteLLM, Chroma, Whisper, all native Python. Fastest path to MVP. | Adds ~80–150 MB to installer (bundled python). Two-process debugging. |
| B. Rust-native (`candle` + `qdrant-client` + `whisper-rs`) | Single binary, smaller. | Half the libraries are immature. LiteLLM has no Rust equivalent. Reinventing wheels. |
| C. Pure JS/Node (LangChain.js) | Single language with frontend. | LiteLLM-equivalent in JS is weaker. Vector store options worse. |

**Pick: A.** Ship the sidecar via `tauri.conf.json` `externalBin`. Use PyOxidizer or PyInstaller to bundle python + deps into a single executable. Health-check it on Tauri startup, restart on crash.

### D2. Local-first vs Cloud-first

| Option | Pros | Cons |
|---|---|---|
| **A. Hybrid, local-first default (recommended)** | Privacy story is killer feature for an "always watching" companion. Cost = $0 for casual users. | Requires user to install Ollama or accept lower-quality 7B model. Voice locally is mediocre. |
| B. Cloud-only | Higher quality across the board. Lower install friction. | Recurring cost. Privacy nightmare with Screen Vision. Hard sell to security-minded users. |
| C. Local-only | Pure privacy. | GPT-4o-tier quality unreachable on consumer hardware in 2025. Voice quality far below ElevenLabs. |

**Pick: A.** First-run wizard asks: "Cloud (best quality, paid keys) / Local (private, needs Ollama) / Hybrid (smart routing)". LiteLLM makes this trivial — same `litellm.completion` call works for both. Vision and TTS default to cloud (quality gap too large) but expose a "fully local" toggle.

### D3. Memory extraction: every turn vs batched

The scope says "after every conversation turn." Realistically:
- Extractor on every turn = 1 extra LLM call per turn = +$$ + +latency.
- Most turns ("hahaha", "ok", "what about you?") have **nothing memorable**.

**Pick: hybrid.**
- Cheap heuristic gate first (length > 30 chars **and** contains at least one of: pronouns, dates, named entities, numbers, "always"/"never"/"hate"/"love"/"my"/"I'm").
- If gate passes, run extractor with a small fast model (`gpt-4o-mini` or local `qwen2.5:3b`).
- Hard cap: max 1 extraction per 5 turns even if gate keeps firing — flush on session end.

### D4. Screen Vision — privacy + cost design

This is the riskiest module. Sending screenshots to a cloud LLM every 10s is:
- ~360/hour × $0.01 = ~$3.60/hour with GPT-4o = **unshippable**.
- A wiretap from the user's perspective unless designed with consent first.

**Pick: aggressive default-off, local-first design.**
1. **Off by default.** Onboarding has a separate, prominent opt-in screen.
2. **Trigger model**: not fixed interval. Capture on (a) window/app focus change, (b) user-initiated "look at this" hotkey, (c) configurable idle interval (default 5 min, not 10 s).
3. **App allowlist / blocklist**: user picks which apps companion can see. Hard block on apps matching `password|bank|secret|1password|bitwarden|...`.
4. **Region masking**: optional rectangles to always blur (e.g. cover terminal area, cover top of browser where URL lives).
5. **Local vision option**: `moondream2` or `llava-phi3` runs in Ollama. Free, private, "good enough" for "user is reading a webpage about X."
6. **Visible indicator**: small dot on the sprite turns red while a frame is being captured. Always.
7. **No frame retention**: vision LLM returns text note → frame is discarded immediately, never written to disk.

### D5. Avatar: Rive vs Ready Player Me vs MetaHuman

| Option | Fidelity | Runtime cost | Effort |
|---|---|---|---|
| **Rive 2D (phase 1)** | Stylized but expressive | Negligible | Low — designer can produce in Rive editor |
| Ready Player Me 3D (phase 2) | Mid (Pixar-ish) | Moderate (three.js) | Medium |
| ~~MetaHuman~~ | Photoreal | **Massive** — requires Unreal runtime, GB-scale assets, GPU | High — almost a separate app |

**Pick: ship Rive, optionally graduate to RPM, drop MetaHuman from scope.** MetaHuman makes sense for a fullscreen virtual-girlfriend kiosk product, not a 200×200 desktop companion that lives in a corner. The fidelity is wasted at that size and the install footprint kills adoption.

### D6. Build order

The scope says "Chat → Voice → Avatar." Modules 5 & 6 (Vision, Desktop Presence) aren't given an explicit slot. My read:

- **Desktop Presence (M6) is not "last", it's the shell.** The always-on-top transparent window IS the app — every other module renders inside or talks to it. So the **Tauri shell with a placeholder sprite must be M0/M1**.
- **Chat in a normal popup window** as the first interactive milestone, so we can iterate on the conversation engine without fighting Tauri's transparent-window quirks.
- **Voice and Avatar are polish layers** added once the brain works.

Revised order:

| Milestone | Goal | Modules touched | "Done when…" |
|---|---|---|---|
| **M0** | Repo scaffolding + Tauri shell + Python sidecar + LiteLLM hello-world | 1 (skeleton) | Type "hi" → streamed reply from configurable model in a normal Tauri window. |
| **M1** | Personality / Companion Card | 3 | Form for name/tone/relationship/backstory → persisted → injected into every prompt. |
| **M2** | Memory: episodic + semantic + extractor + retrieval | 2 | Tell it "I'm a bassoonist." Restart app. Ask "what instrument do I play?" → it knows. |
| **M3** | Desktop Presence shell | 6 | Sprite (static placeholder) lives in screen corner, always-on-top, draggable, click → expands chat panel. Emotion events swap sprite frames. |
| **M4** | Voice (STT + TTS) | 4 (voice) | Hold-to-talk → transcribed → reply streamed and spoken. |
| **M5** | Screen Vision | 5 | Opt-in flow + allowlist + capture-on-focus-change → companion proactively asks once per session. |
| **M6** | Avatar polish | 4 (avatar) | Replace placeholder sprite with full Rive animation set tied to emotion + speaking states. |

Each milestone is shippable on its own as an alpha.

---

## 3. API Contracts (between modules)

These are the internal contracts. Stable contracts mean any module can be rewritten without touching the others.

### 3.1 Conversation Engine

```
POST /chat
  body: { session_id: str, user_message: str }
  → SSE stream of:
       { type: "token", text: str }
       { type: "emotion", value: "happy"|"sad"|"curious"|"flirty"|"concerned"|"neutral" }
       { type: "done", message_id: str, full_text: str }

GET /history?session_id=&limit=
  → [{ id, role, content, ts, emotion? }]
```

### 3.2 Memory System

```
# Episodic
POST /memory/episodic
  body: { content: str, source: "conversation"|"vision", ts: iso, salience: 0..1 }

GET /memory/episodic/search?query=&k=8
  → [{ content, ts, salience, score }]

# Semantic
GET /memory/semantic              → full profile dict
PATCH /memory/semantic            body: { path: "preferences.music.genres", op: "add"|"set"|"remove", value: any }
DELETE /memory/semantic           body: { path }   # for "forget X"
```

### 3.3 Personality

```
GET /personality/card             → current companion card
PUT /personality/card             body: full card object
GET /personality/system_prompt    → compiled prompt string (debug/inspection)
```

Companion card schema:
```json
{
  "name": "string",
  "pronouns": "string",
  "relationship_type": "friend|sibling|partner|mentor|cat",
  "tone": ["warm", "playful", "concise"],
  "backstory": "free text, max 1000 chars",
  "speech_quirks": ["calls user 'kiddo'", "uses lowercase only"],
  "boundaries": ["no roleplay of violence", ...]
}
```

### 3.4 Screen Vision

```
POST /vision/enable          body: { mode: "off"|"on_focus_change"|"interval", interval_sec?: int, allowlist: [str], blocklist: [str] }
GET  /vision/status          → { enabled, last_capture_ts, last_note }
GET  /vision/latest_note     → { content: str, ts } | null    # consumed by Context Builder
```

### 3.5 Voice

```
POST /voice/stt              multipart audio → { text }
POST /voice/tts              body: { text, voice_id? } → audio stream (or url)
```

### 3.6 Tauri ↔ sidecar

- HTTP for request/response and SSE.
- Tauri events for emotion broadcast: `emit('companion://emotion', { value })`.
- Tauri commands for OS-level stuff the Python side can't do as well: window position, register global hotkey, mic permission.

---

## 4. Folder Structure (proposed)

```
companion/
├── apps/
│   ├── desktop/                  # Tauri shell
│   │   ├── src-tauri/            # Rust
│   │   │   ├── src/
│   │   │   │   ├── main.rs
│   │   │   │   ├── window.rs     # always-on-top, transparent
│   │   │   │   ├── sidecar.rs    # spawn + health-check Python
│   │   │   │   ├── hotkey.rs
│   │   │   │   └── ipc.rs
│   │   │   └── tauri.conf.json
│   │   └── src/                  # React frontend
│   │       ├── components/
│   │       │   ├── Sprite.tsx        # Rive
│   │       │   ├── ChatPanel.tsx
│   │       │   ├── CompanionCard.tsx
│   │       │   └── Onboarding/
│   │       ├── hooks/
│   │       │   ├── useChat.ts        # SSE
│   │       │   └── useEmotion.ts     # Tauri event listener
│   │       ├── lib/api.ts            # sidecar HTTP client
│   │       └── App.tsx
│   └── sidecar/                  # Python backend
│       ├── pyproject.toml
│       ├── companion/
│       │   ├── main.py           # FastAPI app
│       │   ├── conversation/
│       │   │   ├── engine.py
│       │   │   ├── context_builder.py
│       │   │   └── emotion_tagger.py
│       │   ├── memory/
│       │   │   ├── episodic.py   # Chroma
│       │   │   ├── semantic.py   # SQLite
│       │   │   ├── extractor.py
│       │   │   └── schema.py
│       │   ├── personality/
│       │   │   ├── card.py
│       │   │   └── prompt_compiler.py
│       │   ├── vision/
│       │   │   ├── worker.py
│       │   │   ├── capture.py    # mss
│       │   │   └── allowlist.py
│       │   ├── voice/
│       │   │   ├── stt.py        # faster-whisper
│       │   │   └── tts.py        # ElevenLabs / Piper
│       │   ├── llm/
│       │   │   └── router.py     # LiteLLM wrapper
│       │   └── settings.py
│       └── tests/
├── packages/
│   ├── shared-types/             # TS types generated from Pydantic
│   └── prompts/                  # versioned prompt templates (yaml)
├── docs/
│   ├── ARCHITECTURE.md           # this file
│   ├── PRIVACY.md
│   └── PROMPTS.md
└── README.md
```

User data lives at `$APPDATA/companion/`:
```
companion/
├── settings.json
├── card.json
├── semantic.sqlite
├── chroma/
└── logs/
```

---

## 5. Prompt Engineering Notes

The "feels like Replika" magic isn't in the code — it's in the prompts. Three prompts that need iteration:

1. **Companion system prompt** — compiled from Companion Card. Must include: identity, tone, relationship framing, hard boundaries, memory-recall instructions, format rules, emotion-tag instructions.
2. **Memory extractor prompt** — given (user_msg, assistant_msg), emit JSON list of `{ kind: "episodic"|"semantic", content, salience, semantic_path? }`. Few-shot heavily. Keep small.
3. **Vision prompt** — given screenshot + companion card, emit one sentence: "User is currently …, in a [focused|distracted|relaxed] state." No essay. No advice. Just observation. Burns less tokens, less hallucination.

All three live in `packages/prompts/*.yaml` with version pins so we can A/B them without code changes.

---

## 6. Risks & Open Questions

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Screen Vision = "spyware" perception | **High** | §D4 — opt-in, local option, allowlist, visible indicator, frame discard. Dedicated PRIVACY.md. |
| R2 | Vision cost spirals if user leaves it on cloud | High | Hard daily $-cap in settings. Force interval ≥ 60s in cloud mode. |
| R3 | Memory extractor produces garbage / contradictions over time | Medium | Periodic "memory consolidation" job that dedupes / resolves contradictions. Surfacing UI: "Here's what I remember about you" + edit/delete. |
| R4 | LiteLLM provider drift / API breakage | Medium | Pin version. Wrap in our own thin interface. Integration tests against mocked providers. |
| R5 | Tauri transparent + always-on-top + non-focusable behaves differently per OS (esp. Linux/Wayland) | Medium | Test matrix. Fallback to "small floating window" mode on broken combos. |
| R6 | Bundling Python sidecar bloats installer | Low–Med | PyInstaller one-file mode + UPX. Realistic target: <120 MB total installer. |
| R7 | Voice latency end-to-end (mic → STT → LLM → TTS) >2s feels unnatural | Medium | Stream STT (Whisper streaming), stream TTS chunks aligned to LLM stream. ElevenLabs supports input streaming. |
| R8 | "Feels like Replika" emotional bond → user attachment / mental-health concerns | **High but non-technical** | Out-of-band: ToS, content boundaries in system prompt, crisis-keyword detector that surfaces hotline links, no encouragement of harmful behavior. |

**Open questions for you:**

1. Target OS for v1? (Recommend: Windows + macOS first, Linux best-effort.)
2. Single user or multi-profile per machine?
3. Monetization shape — free + BYO API key, freemium, or fully cloud subscription? Affects D2 default.
4. Languages — Indonesian + English UI from day one, or English-only MVP?
5. Are you building this solo, with a designer, or a team? Affects whether Rive avatars are realistic in M3 or if we use SVG placeholders.

---

## 7. What I'd Cut From Scope (if forced)

If timeline matters more than feature completeness, in priority order of cuts:

1. **MetaHuman** — drop entirely (see D5).
2. **3D avatar (RPM)** — defer to v1.1; ship with Rive 2D only.
3. **Local TTS (Piper)** — defer; ElevenLabs only at launch with clear API key requirement.
4. **Local STT (faster-whisper)** — defer; OpenAI Whisper API only at launch.
5. **Screen Vision interval mode** — ship only "on focus change" + "manual hotkey"; both are cheaper and less creepy.

After cuts the V1 stack is: Tauri + React + Python sidecar + LiteLLM + Chroma + SQLite + ElevenLabs + Whisper API + Rive. ~6 weeks of focused work for a working alpha.

---

## 8. Next Steps

After you sign off / iterate on this doc:

1. Lock decisions D1–D6.
2. Answer the 5 open questions in §6.
3. I scaffold the M0 milestone (`apps/desktop/` + `apps/sidecar/` + chat hello-world + LiteLLM wired up) into a real repo and PR.
4. Iterate per milestone.
