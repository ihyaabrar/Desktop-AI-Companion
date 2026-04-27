import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Sprite } from "./Sprite";
import { type Emotion, EMOTIONS } from "../lib/emotion";
import { invokeCommand, isTauriRuntime, listenEvent } from "../lib/tauri";

/**
 * Contents of the small always-on-top presence window. The whole tile is a
 * Tauri drag region so the user can move it freely; the sprite itself is the
 * click target that brings the chat window forward.
 */
export function Presence() {
  const { t } = useTranslation();
  const [emotion, setEmotion] = useState<Emotion>("neutral");

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let cancelled = false;
    void (async () => {
      const fn = await listenEvent<string>("emotion-changed", (state) => {
        if (cancelled) return;
        if ((EMOTIONS as readonly string[]).includes(state)) {
          setEmotion(state as Emotion);
        }
      });
      if (cancelled) {
        fn();
      } else {
        unlisten = fn;
      }
    })();
    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

  const handleClick: React.MouseEventHandler = (event) => {
    event.preventDefault();
    void invokeCommand("show_main");
  };

  return (
    <div className="presence" data-tauri-drag-region>
      <button
        type="button"
        className="presence__sprite"
        onClick={handleClick}
        aria-label={t("presence.openChat")}
        title={t("presence.openChat")}
      >
        <Sprite emotion={emotion} size={150} />
      </button>
      {!isTauriRuntime() && <p className="presence__hint">{t("presence.tauriOnlyHint")}</p>}
    </div>
  );
}
