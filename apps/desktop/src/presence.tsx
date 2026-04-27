import React from "react";
import ReactDOM from "react-dom/client";
import { Presence } from "./components/Presence";
import "./i18n";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Presence />
  </React.StrictMode>,
);
