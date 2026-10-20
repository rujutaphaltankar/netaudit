import { SEVERITIES, SEVERITY_HEX, cn } from "../lib/ui";
import type { Severity } from "../types";

/** Stacked bar of failed findings per severity, with an accessible text legend. */
export default function SeverityBar({ counts, className }: { counts: Partial<Record<Severity, number>>; className?: string }) {
  const total = SEVERITIES.reduce((n, s) => n + (counts[s] ?? 0), 0);
  return (
    <div className={className}>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-mist" aria-hidden>
        {SEVERITIES.map((s) => (counts[s] ? <div key={s} style={{ width: `${((counts[s] ?? 0) / total) * 100}%`, background: SEVERITY_HEX[s] }} /> : null))}
      </div>
      <ul className={cn("mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted")}>
        {SEVERITIES.map((s) => (
          <li key={s} className="flex items-center gap-1.5">
            <span className="size-2 rounded-sm" style={{ background: SEVERITY_HEX[s] }} />
            {counts[s] ?? 0} {s}
          </li>
        ))}
      </ul>
    </div>
  );
}
