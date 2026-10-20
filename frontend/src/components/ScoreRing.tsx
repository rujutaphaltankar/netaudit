import { useEffect, useState } from "react";
import { formatScore, gradeHex, ringGeometry } from "../lib/ui";

/** The one memorable element: a ring that fills to the score once, on arrival. */
export default function ScoreRing({ score, grade, size = 168 }: { score: number | null; grade: string; size?: number }) {
  const { circumference, offset } = ringGeometry(score);
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(id);
  }, []);
  const color = gradeHex(grade);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }} role="img" aria-label={`Score ${formatScore(score)} out of 100, grade ${grade}`}>
      <svg viewBox="0 0 128 128" width={size} height={size} className="-rotate-90">
        <circle cx="64" cy="64" r="54" fill="none" stroke="#e3e9ed" strokeWidth="10" />
        <circle
          cx="64" cy="64" r="54" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={drawn ? offset : circumference}
          style={{ transition: "stroke-dashoffset 1100ms cubic-bezier(.2,.7,.2,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-semibold leading-none text-ink">{formatScore(score)}</span>
        <span className="mt-1 text-xs text-muted">of 100</span>
        <span className="mt-1.5 rounded px-2 text-lg font-semibold leading-tight text-white" style={{ background: color }}>{grade}</span>
      </div>
    </div>
  );
}
