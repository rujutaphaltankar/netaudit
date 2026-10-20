import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { compareAudits } from "../api/client";
import { Card, ErrorNote, PageHeader, SeverityBadge, Spinner, StatusBadge, useAsync } from "../components/ui";
import { cn, formatDate, formatScore } from "../lib/ui";
import type { AuditItem } from "../types";

function Side({ label, a }: { label: string; a: AuditItem }) {
  return (
    <Card>
      <div className="text-xs text-muted">{label}</div>
      <Link to={`/audits/${a.id}`} className="font-medium text-ink hover:text-signal">{a.hostname ?? a.filename} (#{a.id})</Link>
      <div className="mt-1 text-3xl font-semibold text-ink">{formatScore(a.score)} <span className="text-base text-muted">grade {a.grade}</span></div>
      <div className="text-xs text-muted">{formatDate(a.created_at)}</div>
    </Card>
  );
}

export default function Compare() {
  const [params] = useSearchParams();
  const base = Number(params.get("base")), target = Number(params.get("target"));
  const { data, error, loading } = useAsync(() => compareAudits(base, target), [base, target]);
  const [showSame, setShowSame] = useState(false);
  if (loading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  const rows = data.changes.filter((c) => showSame || c.change !== "unchanged");
  const delta = data.score_delta;
  return (
    <>
      <p className="mb-2 text-sm"><Link to="/audits" className="text-signal underline">← History</Link></p>
      <PageHeader title="Compare audits" subtitle="Baseline (earlier) versus target (later)." />
      <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <Side label="Baseline" a={data.base} />
        <div className={cn("text-center text-2xl font-semibold", delta === null ? "text-muted" : delta >= 0 ? "text-pass" : "text-crit")}>{delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta}`}</div>
        <Side label="Target" a={data.target} />
      </div>
      <Card className="mt-5 overflow-x-auto p-0">
        <div className="flex items-center justify-between border-b border-line p-3 text-sm">
          <span>{rows.length} rule{rows.length === 1 ? "" : "s"} shown</span>
          <label className="flex items-center gap-2"><input type="checkbox" checked={showSame} onChange={(e) => setShowSame(e.target.checked)} /> Show unchanged</label>
        </div>
        <table className="w-full min-w-[36rem] text-left text-sm"><tbody className="divide-y divide-line">
          {rows.length === 0 && <tr><td className="p-6 text-center text-muted">No differences between these audits.</td></tr>}
          {rows.map((c) => (
            <tr key={c.rule_id}>
              <td className="p-3"><span className="font-mono text-xs text-muted">{c.rule_id}</span><div className="text-ink">{c.title}</div></td>
              <td className="p-3"><SeverityBadge severity={c.severity} /></td>
              <td className="p-3">{c.base_status && <StatusBadge status={c.base_status} />}</td>
              <td className="p-3 text-muted" aria-hidden>→</td>
              <td className="p-3">{c.target_status && <StatusBadge status={c.target_status} />}</td>
              <td className={cn("p-3 text-xs font-medium", c.change === "improved" ? "text-pass" : c.change === "regressed" ? "text-crit" : "text-muted")}>{c.change}</td>
            </tr>
          ))}
        </tbody></table>
      </Card>
    </>
  );
}
