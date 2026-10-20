import { useState } from "react";
import { Chip, SeverityBadge, StatusBadge } from "./ui";
import type { Finding } from "../types";

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="rounded border border-line bg-paper px-2 py-0.5 text-xs text-ink hover:bg-mist"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        } catch { /* clipboard unavailable (insecure context) */ }
      }}
    >
      {done ? "Copied" : "Copy"}
    </button>
  );
}

export default function FindingCard({ f }: { f: Finding }) {
  return (
    <details open={f.status === "fail"} className="group rounded-lg border border-line bg-paper">
      <summary className="flex cursor-pointer flex-wrap items-center gap-2 p-3.5 hover:bg-mist/60">
        <StatusBadge status={f.status} />
        <SeverityBadge severity={f.severity} />
        <span className="font-mono text-xs text-muted">{f.rule_id}</span>
        <span className="min-w-0 flex-1 font-medium text-ink">{f.title}</span>
        <span className="text-muted transition-transform group-open:rotate-90" aria-hidden>›</span>
      </summary>
      <div className="space-y-3 border-t border-line p-4 text-sm">
        <p>{f.message}</p>
        {f.observed !== null && <p className="text-muted">Observed value: <span className="font-mono text-ink">{f.observed}</span></p>}

        {f.evidence.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-medium text-muted">Evidence from the configuration (secrets redacted)</div>
            <pre className="overflow-x-auto rounded-md bg-mist p-3 font-mono text-xs leading-relaxed text-ink">
              {f.evidence.map((e) => `L${e.line_number ?? "?"}  ${e.text}`).join("\n")}
            </pre>
          </div>
        )}

        {f.remediation && (
          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-medium text-muted">Recommended fix</span>
              <CopyButton text={f.remediation} />
            </div>
            <pre className="overflow-x-auto rounded-md bg-ink p-3 font-mono text-xs leading-relaxed text-[#cfe9eb]">{f.remediation}</pre>
          </div>
        )}

        {f.references.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {f.references.map((r) => (
              <span key={r.framework + r.control} title={r.title}><Chip tone="bg-signal-wash text-signal-dark">{r.framework.replace(" Rev. 5", "").replace("ISO/IEC 27001:2022 Annex A", "ISO 27001")} {r.control}</Chip></span>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}
