import { useTranslation } from "react-i18next";
import { ChatPanel } from "./components/ChatPanel";

export default function App() {
  const { t, i18n } = useTranslation();

  const toggleLang = () => {
    i18n.changeLanguage(i18n.language === "id" ? "en" : "id");
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>{t("app.title")}</h1>
        <button type="button" onClick={toggleLang} className="lang-toggle">
          {i18n.language === "id" ? "EN" : "ID"}
        </button>
      </header>
      <main className="app-main">
        <ChatPanel />
      </main>
    </div>
  );
}
