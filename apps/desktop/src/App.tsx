import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChatPanel } from "./components/ChatPanel";
import { CompanionCardForm } from "./components/CompanionCardForm";
import { MemoryInspector } from "./components/MemoryInspector";
import { type CompanionCard, getCard } from "./lib/api";

type Mode = "loading" | "onboarding" | "chat" | "settings" | "memory";

export default function App() {
  const { t, i18n } = useTranslation();
  const [mode, setMode] = useState<Mode>("loading");
  const [card, setCard] = useState<CompanionCard | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

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

  const toggleLang = () => {
    void i18n.changeLanguage(i18n.language === "id" ? "en" : "id");
  };

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
