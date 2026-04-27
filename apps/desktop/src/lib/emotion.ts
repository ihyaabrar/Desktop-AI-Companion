// Tiny keyword-based emotion classifier.
//
// We deliberately stay heuristic: a future milestone can replace this with a
// dedicated sentiment model or a lightweight LLM probe, but for the desktop
// presence sprite the cost of a wrong guess is just a slightly off facial
// expression. Cheap + offline + deterministic wins here.

export type Emotion = "neutral" | "happy" | "thinking" | "listening" | "sad";

export const EMOTIONS: readonly Emotion[] = ["neutral", "happy", "thinking", "listening", "sad"] as const;

const HAPPY =
  /(\b(yay|love|happy|glad|thanks|amazing|awesome|nice|great)\b|senang|hebat|keren|mantap|terima kasih|asyik|seru|❤|😊|😄|🎉)/i;
const SAD =
  /(\b(sorry|sad|unfortunately|sucks|miss(?:ed)?|lonely)\b|maaf|sedih|kasihan|kecewa|sayang sekali|😢|😔)/i;
const THINKING =
  /(\b(hmm+|let me think|let's see|wonder|figuring out|i think|might)\b|sebentar|coba pikir|kayanya|mungkin|menurutku)/i;
const LISTENING =
  /(\b(tell me|how are you|what about you|how was|how did)\b|cerita dong|gimana kabar|gimana ya|kabarmu|kamu sendiri)/i;

/**
 * Map a piece of assistant text to one of the five sprite states.
 * Order matters: explicit positive/negative cues beat the broad "?"
 * fallback so the sprite doesn't read every question as "listening".
 */
export function deriveEmotion(text: string): Emotion {
  if (!text) return "neutral";
  const trimmed = text.trim();
  if (!trimmed) return "neutral";

  if (SAD.test(trimmed)) return "sad";
  if (HAPPY.test(trimmed)) return "happy";
  if (LISTENING.test(trimmed)) return "listening";
  if (THINKING.test(trimmed)) return "thinking";
  if (trimmed.endsWith("?")) return "listening";
  return "neutral";
}
