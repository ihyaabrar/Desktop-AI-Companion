// Tiny client for the Python sidecar. Talks to it over plain HTTP on localhost.

const SIDECAR_URL = (import.meta.env.VITE_SIDECAR_URL as string | undefined) ?? "http://127.0.0.1:8765";

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "done"; session_id: string }
  | { type: "error"; message: string };

export interface StreamChatArgs {
  userMessage: string;
  sessionId?: string;
  signal?: AbortSignal;
  onEvent: (event: ChatEvent) => void;
}

/**
 * Stream a chat reply from the sidecar via Server-Sent Events.
 *
 * The sidecar emits `data: <json>\n\n` frames; we parse them as they arrive
 * and invoke `onEvent` for each. Returns a promise that resolves once the
 * stream ends (after the `done` event) or rejects on transport failure.
 */
export async function streamChat({ userMessage, sessionId, signal, onEvent }: StreamChatArgs): Promise<void> {
  const response = await fetch(`${SIDECAR_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_message: userMessage,
      session_id: sessionId ?? crypto.randomUUID(),
    }),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`Sidecar returned ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by blank lines.
    let separatorIdx: number;
    while ((separatorIdx = buffer.indexOf("\n\n")) !== -1) {
      const rawFrame = buffer.slice(0, separatorIdx);
      buffer = buffer.slice(separatorIdx + 2);

      for (const line of rawFrame.split("\n")) {
        if (!line.startsWith("data:")) continue;
        const payload = line.slice("data:".length).trim();
        if (!payload) continue;
        try {
          onEvent(JSON.parse(payload) as ChatEvent);
        } catch {
          // Ignore malformed frames — sidecar is the source of truth.
        }
      }
    }
  }
}

export async function checkHealth(): Promise<{
  status: string;
  model: string;
  version: string;
}> {
  const resp = await fetch(`${SIDECAR_URL}/health`);
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json() as Promise<{
    status: string;
    model: string;
    version: string;
  }>;
}

// ----------------------------- Personality -----------------------------------

export type RelationshipType = "friend" | "sibling" | "partner" | "mentor" | "cat" | "other";
export type CardLanguage = "id" | "en" | "mixed";

export interface CompanionCard {
  name: string;
  pronouns: string;
  relationship_type: RelationshipType;
  tone: string[];
  backstory: string;
  speech_quirks: string[];
  boundaries: string[];
  language: CardLanguage;
}

export const DEFAULT_CARD: CompanionCard = {
  name: "Companion",
  pronouns: "they/them",
  relationship_type: "friend",
  tone: ["warm", "playful", "concise"],
  backstory: "",
  speech_quirks: [],
  boundaries: [],
  language: "mixed",
};

export async function getCard(): Promise<CompanionCard | null> {
  const resp = await fetch(`${SIDECAR_URL}/personality/card`);
  if (!resp.ok) throw new Error(`getCard failed: ${resp.status}`);
  return (await resp.json()) as CompanionCard | null;
}

export async function saveCard(card: CompanionCard): Promise<CompanionCard> {
  const resp = await fetch(`${SIDECAR_URL}/personality/card`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(card),
  });
  if (!resp.ok) throw new Error(`saveCard failed: ${resp.status}`);
  return (await resp.json()) as CompanionCard;
}

export async function resetCard(): Promise<void> {
  const resp = await fetch(`${SIDECAR_URL}/personality/card`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`resetCard failed: ${resp.status}`);
}
