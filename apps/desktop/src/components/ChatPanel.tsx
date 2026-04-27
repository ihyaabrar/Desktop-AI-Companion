import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { streamChat, type ChatEvent } from "../lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  pending?: boolean;
  error?: boolean;
}

export function ChatPanel() {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionIdRef = useRef<string>(crypto.randomUUID());

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || busy) return;

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", text };
    const assistantId = crypto.randomUUID();
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      text: "",
      pending: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setBusy(true);

    const updateAssistant = (mut: (m: Message) => Message) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? mut(m) : m)),
      );
    };

    try {
      await streamChat({
        userMessage: text,
        sessionId: sessionIdRef.current,
        onEvent: (ev: ChatEvent) => {
          if (ev.type === "token") {
            updateAssistant((m) => ({
              ...m,
              text: m.text + ev.text,
              pending: false,
            }));
          } else if (ev.type === "error") {
            updateAssistant((m) => ({
              ...m,
              text: t("chat.errorPrefix") + ev.message,
              pending: false,
              error: true,
            }));
          }
        },
      });
    } catch {
      updateAssistant((m) => ({
        ...m,
        text: t("chat.connectionError"),
        pending: false,
        error: true,
      }));
    } finally {
      setBusy(false);
    }
  }, [busy, input, t]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  };

  return (
    <section className="chat-panel">
      <ol className="chat-log" aria-live="polite">
        {messages.map((m) => (
          <li
            key={m.id}
            className={`chat-msg chat-msg--${m.role}${m.error ? " chat-msg--error" : ""}`}
          >
            <span className="chat-msg__role">
              {m.role === "user" ? t("chat.you") : t("chat.companion")}
            </span>
            <span className="chat-msg__text">
              {m.text || (m.pending ? <em>{t("chat.thinking")}</em> : null)}
            </span>
          </li>
        ))}
      </ol>
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t("chat.placeholder")}
          disabled={busy}
        />
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={busy || !input.trim()}
        >
          {t("chat.send")}
        </button>
      </div>
    </section>
  );
}
