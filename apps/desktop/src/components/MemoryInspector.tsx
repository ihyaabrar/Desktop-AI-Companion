import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type EpisodicMemory,
  type SemanticFact,
  clearEpisodicMemories,
  deleteSemanticFact,
  listEpisodicMemories,
  listSemanticFacts,
} from "../lib/api";

interface MemoryInspectorProps {
  onClose: () => void;
}

export function MemoryInspector({ onClose }: MemoryInspectorProps) {
  const { t } = useTranslation();
  const [facts, setFacts] = useState<SemanticFact[]>([]);
  const [episodes, setEpisodes] = useState<EpisodicMemory[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [f, e] = await Promise.all([listSemanticFacts(), listEpisodicMemories(50)]);
      setFacts(f);
      setEpisodes(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const onDeleteFact = async (key: string) => {
    try {
      await deleteSemanticFact(key);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onClearEpisodes = async () => {
    try {
      await clearEpisodicMemories();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <section className="memory-inspector">
      <header className="memory-inspector__header">
        <h2>{t("memory.title")}</h2>
        <button type="button" className="btn-ghost" onClick={onClose}>
          {t("memory.close")}
        </button>
      </header>

      {error && <p className="app-status app-status--error">{error}</p>}
      {loading && <p className="app-status">{t("memory.loading")}</p>}

      <section className="memory-inspector__section">
        <div className="memory-inspector__section-header">
          <h3>{t("memory.semanticTitle")}</h3>
          <span className="memory-inspector__count">{facts.length}</span>
        </div>
        {facts.length === 0 ? (
          <p className="memory-inspector__empty">{t("memory.semanticEmpty")}</p>
        ) : (
          <ul className="memory-inspector__list">
            {facts.map((f) => (
              <li key={f.key} className="memory-inspector__fact">
                <div>
                  <strong>{f.key}</strong>
                  <span className="memory-inspector__value">: {JSON.stringify(f.value)}</span>
                  {f.evidence && <p className="memory-inspector__evidence">&ldquo;{f.evidence}&rdquo;</p>}
                </div>
                <button
                  type="button"
                  className="btn-ghost btn-ghost--small"
                  onClick={() => void onDeleteFact(f.key)}
                  aria-label={t("memory.deleteFact")}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="memory-inspector__section">
        <div className="memory-inspector__section-header">
          <h3>{t("memory.episodicTitle")}</h3>
          <span className="memory-inspector__count">{episodes.length}</span>
          {episodes.length > 0 && (
            <button
              type="button"
              className="btn-ghost btn-ghost--small"
              onClick={() => void onClearEpisodes()}
            >
              {t("memory.clearEpisodic")}
            </button>
          )}
        </div>
        {episodes.length === 0 ? (
          <p className="memory-inspector__empty">{t("memory.episodicEmpty")}</p>
        ) : (
          <ul className="memory-inspector__list">
            {episodes.map((e) => (
              <li key={e.id} className="memory-inspector__episode">
                {e.text}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
