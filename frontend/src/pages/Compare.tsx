import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { compareAudits } from "../api/client";
import { Card, ErrorNote, PageHeader, SeverityBadge, Spinner, StatusBadge, useAsync } from "../components/ui";
import { cn, formatDate, formatScore, gradeHex } from "../lib/ui";
import type { AuditItem } from "../types";

function Side({ label, a }: { label: string; a: AuditItem }) {
  return (
    <Card className="relative overflow-hidden">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</span>
        <span
          className="grid size-6 place-items-center rounded text-xs font-bold text-white shadow-xs"
          style={{ background: gradeHex(a.grade) }}
        >
          {a.grade}
        </span>
      </div>
      <Link to={`/audits/${a.id}`} className="mt-1 block font-semibold text-ink hover:text-signal transition-colors truncate">
        {a.hostname ?? a.filename} (#{a.id})
      </Link>
      <div className="mt-2 text-3xl font-bold text-ink">
        {formatScore(a.score)} <span className="text-sm font-normal text-muted">/ 100</span>
      </div>
      <div className="mt-1 text-xs text-muted">{formatDate(a.created_at)}</div>
    </Card>
  );
}

export default function Compare() {
  const [params] = useSearchParams();
  const base = Number(params.get("base")),
    target = Number(params.get("target"));
  const { data, error, loading } = useAsync(() => compareAudits(base, target), [base, target]);
  const [filterType, setFilterType] = useState<"all" | "diff" | "improved" | "regressed">("diff");

  if (loading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;

  const delta = data.score_delta;
  const rows = data.changes.filter((c) => {
    if (filterType === "all") return true;
    if (filterType === "diff") return c.change !== "unchanged";
    if (filterType === "improved") return c.change === "improved";
    if (filterType === "regressed") return c.change === "regressed";
    return true;
  });

  const improvedCount = data.changes.filter((c) => c.change === "improved").length;
  const regressedCount = data.changes.filter((c) => c.change === "regressed").length;

  return (
    <>
      <p className="mb-2 text-sm">
        <Link to="/audits" className="text-signal underline hover:text-signal-dark">
          ← Back to History
        </Link>
      </p>
      <PageHeader
        title="Audit Drift Comparison"
        subtitle="Side-by-side compliance delta between earlier baseline configuration and target deployment."
      />

      <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <Side label="Baseline (Earlier)" a={data.base} />
        <div className="flex flex-col items-center justify-center p-3">
          <div
            className={cn(
              "rounded-xl px-4 py-2 text-center text-xl font-bold shadow-xs",
              delta === null
                ? "bg-mist text-muted"
                : delta > 0
                ? "bg-pass-wash text-pass ring-1 ring-pass/20"
                : delta < 0
                ? "bg-crit-wash text-crit ring-1 ring-crit/20"
                : "bg-mist text-ink"
            )}
          >
            {delta === null ? "—" : `${delta > 0 ? "+" : ""}${delta} pts`}
          </div>
          <span className="mt-1 text-xs text-muted font-medium">Score Delta</span>
        </div>
        <Side label="Target (Later)" a={data.target} />
      </div>

      <Card className="mt-5 overflow-x-auto p-0 shadow-xs">
        <div className="flex flex-wrap items-center justify-between border-b border-line bg-mist/30 p-3 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setFilterType("diff")}
              className={cn(
                "rounded-full px-3 py-1 font-medium transition-colors",
                filterType === "diff" ? "bg-ink text-white" : "border border-line bg-paper text-ink hover:bg-mist"
              )}
            >
              Differences ({improvedCount + regressedCount})
            </button>
            <button
              type="button"
              onClick={() => setFilterType("improved")}
              className={cn(
                "rounded-full px-3 py-1 font-medium transition-colors",
                filterType === "improved" ? "bg-pass text-white" : "border border-line bg-paper text-ink hover:bg-mist"
              )}
            >
              Improved ({improvedCount})
            </button>
            <button
              type="button"
              onClick={() => setFilterType("regressed")}
              className={cn(
                "rounded-full px-3 py-1 font-medium transition-colors",
                filterType === "regressed" ? "bg-crit text-white" : "border border-line bg-paper text-ink hover:bg-mist"
              )}
            >
              Regressed ({regressedCount})
            </button>
            <button
              type="button"
              onClick={() => setFilterType("all")}
              className={cn(
                "rounded-full px-3 py-1 font-medium transition-colors",
                filterType === "all" ? "bg-ink text-white" : "border border-line bg-paper text-ink hover:bg-mist"
              )}
            >
              All Rules ({data.changes.length})
            </button>
          </div>
          <span className="text-muted">{rows.length} rule{rows.length === 1 ? "" : "s"} displayed</span>
        </div>

        <table className="w-full min-w-[36rem] text-left text-sm">
          <thead className="border-b border-line bg-mist/20 text-xs font-semibold text-muted uppercase">
            <tr>
              <th className="p-3">Rule</th>
              <th className="p-3">Severity</th>
              <th className="p-3">Baseline</th>
              <th className="p-3 w-6 text-center"></th>
              <th className="p-3">Target</th>
              <th className="p-3 text-right">Change</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-muted">
                  No rule results match the selected filter.
                </td>
              </tr>
            )}
            {rows.map((c) => (
              <tr key={c.rule_id} className="hover:bg-mist/40 transition-colors">
                <td className="p-3">
                  <span className="font-mono text-xs text-muted mr-1.5">{c.rule_id}</span>
                  <div className="font-medium text-ink">{c.title}</div>
                </td>
                <td className="p-3">
                  <SeverityBadge severity={c.severity} />
                </td>
                <td className="p-3">{c.base_status && <StatusBadge status={c.base_status} />}</td>
                <td className="p-3 text-center text-muted font-bold" aria-hidden>
                  →
                </td>
                <td className="p-3">{c.target_status && <StatusBadge status={c.target_status} />}</td>
                <td className="p-3 text-right">
                  <span
                    className={cn(
                      "inline-block rounded px-2 py-0.5 text-xs font-bold uppercase tracking-wider",
                      c.change === "improved"
                        ? "bg-pass-wash text-pass"
                        : c.change === "regressed"
                        ? "bg-crit-wash text-crit"
                        : "bg-mist text-muted"
                    )}
                  >
                    {c.change}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
