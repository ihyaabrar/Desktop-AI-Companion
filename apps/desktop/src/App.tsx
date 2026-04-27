import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChatPanel } from "./components/ChatPanel";
import { CompanionCardForm } from "./components/CompanionCardForm";
import { MemoryInspector } from "./components/MemoryInspector";
import { type CompanionCard, getCard } from "./lib/api";
import { invokeCommand, isTauriRuntime } from "./lib/tauri";

const PRESENCE_PREF_KEY = "companion.presence.enabled";

function readPresencePref(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(PRESENCE_PREF_KEY) === "1";
}

type Mode = "loading" | "onboarding" | "chat" | "settings" | "memory";

export default function App() {
  const { t, i18n } = useTranslation();
  const [mode, setMode] = useState<Mode>("loading");
  const [card, setCard] = useState<CompanionCard | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [presenceOn, setPresenceOn] = useState<boolean>(() => readPresencePref());

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const fetched = await getCard();
        if (cancelled) return;
        setCard(fetched);
        setMode(fetched ? "chat" : "onboarding");
      } catch (err) {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : String(err));
        // Sidecar unreachable on launch — let the user see the chat shell anyway,
        // they'll get a clearer error from the chat panel when they try to send.
        setMode("chat");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Sync the OS-level presence window every time the toggle flips. We persist
  // the user's choice ourselves so a fresh launch can hydrate without a round
  // trip to Rust just to read the previous value.
  useEffect(() => {
    window.localStorage.setItem(PRESENCE_PREF_KEY, presenceOn ? "1" : "0");
    void invokeCommand("set_presence_visible", { visible: presenceOn });
  }, [presenceOn]);

  const toggleLang = () => {
    void i18n.changeLanguage(i18n.language === "id" ? "en" : "id");
  };

  const togglePresence = () => setPresenceOn((p) => !p);

  const handleSaved = (saved: CompanionCard) => {
    setCard(saved);
    setMode("chat");
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>{card?.name ?? t("app.title")}</h1>
        <div className="app-header__actions">
          {mode === "chat" && (
            <>
              <button
                type="button"
                className="icon-btn"
                onClick={() => setMode("memory")}
                aria-label={t("app.openMemory")}
                title={t("app.openMemory")}
              >
                🧠
              </button>
              {isTauriRuntime() && (
                <button
                  type="button"
                  className={`icon-btn${presenceOn ? " icon-btn--active" : ""}`}
                  onClick={togglePresence}
                  aria-pressed={presenceOn}
                  aria-label={t(presenceOn ? "app.hidePresence" : "app.showPresence")}
                  title={t(presenceOn ? "app.hidePresence" : "app.showPresence")}
                >
                  {presenceOn ? "🪟" : "💤"}
                </button>
              )}
              <button
                type="button"
                className="icon-btn"
                onClick={() => setMode("settings")}
                aria-label={t("app.openSettings")}
                title={t("app.openSettings")}
              >
                ⚙
              </button>
            </>
          )}
          <button type="button" onClick={toggleLang} className="lang-toggle">
            {i18n.language === "id" ? "EN" : "ID"}
          </button>
        </div>
      </header>
      <main className="app-main">
        {mode === "loading" && <p className="app-status">{t("app.loading")}</p>}
        {mode === "onboarding" && <CompanionCardForm initial={null} onSaved={handleSaved} />}
        {mode === "chat" && (
          <>
            {loadError && (
              <p className="app-status app-status--error">
                {t("app.sidecarUnreachable")} {loadError}
              </p>
            )}
            <ChatPanel />
          </>
        )}
        {mode === "settings" && (
          <CompanionCardForm initial={card} onSaved={handleSaved} onCancel={() => setMode("chat")} />
        )}
        {mode === "memory" && <MemoryInspector onClose={() => setMode("chat")} />}
      </main>
    </div>
  );
}
