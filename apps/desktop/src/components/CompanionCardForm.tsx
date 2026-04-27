import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  type CardLanguage,
  type CompanionCard,
  DEFAULT_CARD,
  type RelationshipType,
  saveCard,
} from "../lib/api";

interface Props {
  initial: CompanionCard | null;
  onSaved: (card: CompanionCard) => void;
  onCancel?: () => void;
}

const RELATIONSHIP_OPTIONS: RelationshipType[] = ["friend", "sibling", "partner", "mentor", "cat", "other"];

const LANGUAGE_OPTIONS: CardLanguage[] = ["mixed", "id", "en"];

function splitList(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function joinList(values: string[]): string {
  return values.join("\n");
}

export function CompanionCardForm({ initial, onSaved, onCancel }: Props) {
  const { t } = useTranslation();
  const [card, setCard] = useState<CompanionCard>(initial ?? DEFAULT_CARD);
  const [toneText, setToneText] = useState(joinList((initial ?? DEFAULT_CARD).tone));
  const [quirksText, setQuirksText] = useState(joinList((initial ?? DEFAULT_CARD).speech_quirks));
  const [boundariesText, setBoundariesText] = useState(joinList((initial ?? DEFAULT_CARD).boundaries));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initial) {
      setCard(initial);
      setToneText(joinList(initial.tone));
      setQuirksText(joinList(initial.speech_quirks));
      setBoundariesText(joinList(initial.boundaries));
    }
  }, [initial]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    const payload: CompanionCard = {
      ...card,
      name: card.name.trim() || DEFAULT_CARD.name,
      pronouns: card.pronouns.trim() || DEFAULT_CARD.pronouns,
      backstory: card.backstory.trim(),
      tone: splitList(toneText),
      speech_quirks: splitList(quirksText),
      boundaries: splitList(boundariesText),
    };
    try {
      const saved = await saveCard(payload);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card-form" onSubmit={handleSubmit}>
      <header className="card-form__header">
        <h2>{t("card.title")}</h2>
        <p className="card-form__subtitle">{t("card.subtitle")}</p>
      </header>

      <label className="card-form__field">
        <span>{t("card.name")}</span>
        <input
          type="text"
          value={card.name}
          onChange={(e) => setCard({ ...card, name: e.target.value })}
          maxLength={60}
          required
        />
      </label>

      <label className="card-form__field">
        <span>{t("card.pronouns")}</span>
        <input
          type="text"
          value={card.pronouns}
          onChange={(e) => setCard({ ...card, pronouns: e.target.value })}
          maxLength={40}
          placeholder="she/her, he/him, they/them, …"
        />
      </label>

      <label className="card-form__field">
        <span>{t("card.relationship")}</span>
        <select
          value={card.relationship_type}
          onChange={(e) => setCard({ ...card, relationship_type: e.target.value as RelationshipType })}
        >
          {RELATIONSHIP_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {t(`card.relationshipOptions.${opt}`)}
            </option>
          ))}
        </select>
      </label>

      <label className="card-form__field">
        <span>{t("card.language")}</span>
        <select
          value={card.language}
          onChange={(e) => setCard({ ...card, language: e.target.value as CardLanguage })}
        >
          {LANGUAGE_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {t(`card.languageOptions.${opt}`)}
            </option>
          ))}
        </select>
      </label>

      <label className="card-form__field">
        <span>{t("card.tone")}</span>
        <textarea
          rows={2}
          value={toneText}
          onChange={(e) => setToneText(e.target.value)}
          placeholder={t("card.tonePlaceholder")}
        />
      </label>

      <label className="card-form__field">
        <span>{t("card.backstory")}</span>
        <textarea
          rows={3}
          value={card.backstory}
          onChange={(e) => setCard({ ...card, backstory: e.target.value })}
          maxLength={1000}
          placeholder={t("card.backstoryPlaceholder")}
        />
      </label>

      <label className="card-form__field">
        <span>{t("card.quirks")}</span>
        <textarea
          rows={2}
          value={quirksText}
          onChange={(e) => setQuirksText(e.target.value)}
          placeholder={t("card.quirksPlaceholder")}
        />
      </label>

      <label className="card-form__field">
        <span>{t("card.boundaries")}</span>
        <textarea
          rows={2}
          value={boundariesText}
          onChange={(e) => setBoundariesText(e.target.value)}
          placeholder={t("card.boundariesPlaceholder")}
        />
      </label>

      {error && <p className="card-form__error">{error}</p>}

      <div className="card-form__actions">
        {onCancel && (
          <button type="button" className="btn-ghost" onClick={onCancel} disabled={busy}>
            {t("card.cancel")}
          </button>
        )}
        <button type="submit" disabled={busy}>
          {busy ? t("card.saving") : t("card.save")}
        </button>
      </div>
    </form>
  );
}
