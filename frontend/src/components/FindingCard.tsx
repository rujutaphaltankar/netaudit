import { useState } from "react";
import { useToast } from "../context/ToastContext";
import { Chip, SeverityBadge, StatusBadge } from "./ui";
import type { Finding } from "../types";

function CopyButton({ text, label = "Copy", successMsg }: { text: string; label?: string; successMsg?: string }) {
  const [done, setDone] = useState(false);
  const toast = useToast();

  async function handleCopy(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      toast.success(successMsg ?? `${label} copied to clipboard`);
      setTimeout(() => setDone(false), 1500);
    } catch {
      toast.error("Unable to copy to clipboard");
    }
  }

  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 rounded border border-line bg-paper px-2 py-0.5 text-xs font-medium text-ink transition-colors hover:bg-mist hover:text-signal"
      onClick={handleCopy}
      title={`Copy ${label.toLowerCase()}`}
    >
      <span>{done ? "✓" : "📋"}</span>
      <span>{done ? "Copied" : label}</span>
    </button>
  );
}

export default function FindingCard({ f, forceOpen }: { f: Finding; forceOpen?: boolean }) {
  const [isOpen, setIsOpen] = useState(forceOpen ?? f.status === "fail");

  const borderAccent = {
    fail: {
      critical: "border-l-4 border-l-crit",
      high: "border-l-4 border-l-high",
      medium: "border-l-4 border-l-med",
      low: "border-l-4 border-l-low",
    }[f.severity],
    pass: "border-l-4 border-l-pass/50",
    unknown: "border-l-4 border-l-med/50",
    not_applicable: "border-l-4 border-l-unk/30",
  }[f.status];

  const evidenceText = f.evidence.map((e) => `L${e.line_number ?? "?"}  ${e.text}`).join("\n");

  return (
    <details
      open={forceOpen !== undefined ? forceOpen : isOpen}
      onToggle={(e) => setIsOpen((e.target as HTMLDetailsElement).open)}
      className={`group rounded-lg border border-line bg-paper transition-shadow hover:shadow-sm ${borderAccent}`}
    >
      <summary className="flex cursor-pointer flex-wrap items-center gap-2 p-3.5 select-none hover:bg-mist/60">
        <StatusBadge status={f.status} />
        <SeverityBadge severity={f.severity} />
        <span className="font-mono text-xs text-muted font-medium">{f.rule_id}</span>
        <span className="min-w-0 flex-1 font-medium text-ink">{f.title}</span>
        <span className="text-muted transition-transform group-open:rotate-90 text-sm font-bold" aria-hidden>
          ›
        </span>
      </summary>
      <div className="space-y-3.5 border-t border-line p-4 text-sm animate-fade-in">
        <p className="leading-relaxed text-body">{f.message}</p>
        {f.observed !== null && (
          <p className="text-muted text-xs">
            Observed value: <span className="font-mono text-ink bg-mist px-1.5 py-0.5 rounded">{f.observed}</span>
          </p>
        )}

        {f.evidence.length > 0 && (
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-semibold text-muted">Evidence from configuration (redacted)</span>
              <CopyButton text={evidenceText} label="Copy evidence" successMsg="Evidence copied to clipboard" />
            </div>
            <pre className="overflow-x-auto rounded-md bg-mist p-3 font-mono text-xs leading-relaxed text-ink border border-line/60">
              {evidenceText}
            </pre>
          </div>
        )}

        {f.remediation && (
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <span className="text-xs font-semibold text-muted">Recommended remediation</span>
              <CopyButton text={f.remediation} label="Copy fix" successMsg="Remediation commands copied to clipboard" />
            </div>
            <pre className="overflow-x-auto rounded-md bg-ink p-3 font-mono text-xs leading-relaxed text-[#cfe9eb] shadow-inner">
              {f.remediation}
            </pre>
          </div>
        )}

        {f.references.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-xs text-muted mr-1">Compliance:</span>
            {f.references.map((r) => (
              <span key={r.framework + r.control} title={r.title}>
                <Chip tone="bg-signal-wash text-signal-dark font-medium">
                  {r.framework.replace(" Rev. 5", "").replace("ISO/IEC 27001:2022 Annex A", "ISO 27001")} {r.control}
                </Chip>
              </span>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}
