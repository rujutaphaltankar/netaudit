import { useState } from "react";
import { Link } from "react-router-dom";
import { reviewMapping } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Chip, ErrorNote } from "./ui";
import type { AIMapping } from "../types";

const IMPACT_TONE = { positive: "bg-pass-wash text-pass", negative: "bg-crit-wash text-crit", neutral: "bg-unk-wash text-unk", unknown: "bg-med-wash text-med" };
const SOURCE_LABEL = { ai: "AI suggestion", heuristic: "Rule-based suggestion", reused: "Reused approved mapping" };
const STATUS_TONE = { pending: "bg-med-wash text-med", approved: "bg-pass-wash text-pass", rejected: "bg-unk-wash text-unk" };

export default function MappingCard({ m, onChanged, showAudit }: { m: AIMapping; onChanged: () => void; showAudit?: boolean }) {
  const { isAdmin } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function decide(decision: "approved" | "rejected") {
    setBusy(true);
    setError(null);
    try {
      await reviewMapping(m.id, decision);
      onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-line bg-paper p-4 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <code className="break-all rounded bg-mist px-2 py-1 font-mono text-xs text-ink">{m.line_number ? `L${m.line_number}  ` : ""}{m.command_text}</code>
        <Chip tone={STATUS_TONE[m.status]}>{m.status}</Chip>
      </div>
      <p className="mt-3 text-ink">{m.meaning}</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <Chip>{m.category}</Chip>
        <Chip tone={IMPACT_TONE[m.security_impact]}>impact: {m.security_impact}</Chip>
        <Chip>confidence: {m.confidence}</Chip>
        <Chip tone="bg-signal-wash text-signal-dark">{SOURCE_LABEL[m.source]}</Chip>
        {m.suggested_field && <Chip>related: {m.suggested_field}</Chip>}
      </div>
      {m.note && <p className="mt-2 text-xs text-muted">{m.note}</p>}
      {showAudit && <p className="mt-2 text-xs text-muted">From <Link className="text-signal underline" to={`/audits/${m.audit_id}`}>{m.audit_filename ?? `audit #${m.audit_id}`}</Link></p>}
      {isAdmin && (
        <div className="mt-3 flex gap-2">
          {m.status !== "approved" && <Button variant="primary" disabled={busy} onClick={() => decide("approved")}>Approve</Button>}
          {m.status !== "rejected" && <Button disabled={busy} onClick={() => decide("rejected")}>Reject</Button>}
        </div>
      )}
      <div className="mt-2"><ErrorNote error={error} /></div>
    </div>
  );
}
