import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import id from "./id.json";

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    id: { translation: id },
  },
  lng: navigator.language.startsWith("id") ? "id" : "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
