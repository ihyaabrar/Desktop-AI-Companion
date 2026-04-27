import type { Emotion } from "../lib/emotion";

interface SpriteProps {
  emotion: Emotion;
  size?: number;
}

interface Expression {
  eyes: React.ReactNode;
  mouth: React.ReactNode;
  hue: string;
}

const EXPRESSIONS: Record<Emotion, Expression> = {
  neutral: {
    hue: "#8a7cff",
    eyes: (
      <>
        <circle cx="38" cy="48" r="4" fill="#1a1a22" />
        <circle cx="62" cy="48" r="4" fill="#1a1a22" />
      </>
    ),
    mouth: (
      <path d="M40 68 Q50 72 60 68" stroke="#1a1a22" strokeWidth="3" fill="none" strokeLinecap="round" />
    ),
  },
  happy: {
    hue: "#ffb86b",
    eyes: (
      <>
        <path d="M32 48 Q38 42 44 48" stroke="#1a1a22" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M56 48 Q62 42 68 48" stroke="#1a1a22" strokeWidth="3" fill="none" strokeLinecap="round" />
      </>
    ),
    mouth: (
      <path d="M36 64 Q50 78 64 64" stroke="#1a1a22" strokeWidth="3" fill="none" strokeLinecap="round" />
    ),
  },
  thinking: {
    hue: "#7cd8ff",
    eyes: (
      <>
        <circle cx="38" cy="48" r="3.5" fill="#1a1a22" />
        <path d="M58 48 L66 48" stroke="#1a1a22" strokeWidth="3" strokeLinecap="round" />
      </>
    ),
    mouth: <path d="M42 70 L58 68" stroke="#1a1a22" strokeWidth="3" strokeLinecap="round" />,
  },
  listening: {
    hue: "#a8ff8a",
    eyes: (
      <>
        <circle cx="38" cy="48" r="5" fill="#1a1a22" />
        <circle cx="62" cy="48" r="5" fill="#1a1a22" />
        <circle cx="40" cy="46" r="1.5" fill="#fff" />
        <circle cx="64" cy="46" r="1.5" fill="#fff" />
      </>
    ),
    mouth: <circle cx="50" cy="70" r="3.5" fill="#1a1a22" />,
  },
  sad: {
    hue: "#7c8aff",
    eyes: (
      <>
        <path d="M32 50 Q38 55 44 50" stroke="#1a1a22" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M56 50 Q62 55 68 50" stroke="#1a1a22" strokeWidth="3" fill="none" strokeLinecap="round" />
      </>
    ),
    mouth: (
      <path d="M36 72 Q50 64 64 72" stroke="#1a1a22" strokeWidth="3" fill="none" strokeLinecap="round" />
    ),
  },
};

/**
 * A round, friendly placeholder sprite. The face changes per `emotion` so the
 * presence window has visible feedback to chat state. Pure SVG so it scales,
 * costs nothing to render, and works without any Rive runtime — that asset
 * pipeline can swap in here later without touching consumers.
 */
export function Sprite({ emotion, size = 140 }: SpriteProps) {
  const expr = EXPRESSIONS[emotion];
  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      role="img"
      aria-label={`Companion mood: ${emotion}`}
      data-emotion={emotion}
    >
      <defs>
        <radialGradient id={`sprite-glow-${emotion}`} cx="50%" cy="40%" r="60%">
          <stop offset="0%" stopColor={expr.hue} stopOpacity="0.95" />
          <stop offset="100%" stopColor={expr.hue} stopOpacity="0.4" />
        </radialGradient>
      </defs>
      <circle cx="50" cy="50" r="42" fill={`url(#sprite-glow-${emotion})`} />
      <circle cx="50" cy="50" r="38" fill={expr.hue} stroke="#0008" strokeWidth="1" />
      {expr.eyes}
      {expr.mouth}
    </svg>
  );
}
