import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { deleteAudit, downloadReport, generateMappings, getAudit } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import FindingCard from "../components/FindingCard";
import MappingCard from "../components/MappingCard";
import ParsedConfig from "../components/ParsedConfig";
import ScoreRing from "../components/ScoreRing";
import SeverityBar from "../components/SeverityBar";
import { Button, Card, Chip, Empty, ErrorNote, PageHeader, Spinner, inputCls, useAsync } from "../components/ui";
import { useToast } from "../context/ToastContext";
import { countByStatus, filterFindings, type FindingFilter } from "../lib/findings";
import { SEVERITIES, STATUS_LABEL, cn, formatDate, vendorLabel } from "../lib/ui";
import type { AuditDetail, FindingStatus, GenerateResult } from "../types";

type Tab = "findings" | "config" | "unknown";

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-md bg-mist px-3 py-2">
      <div className={cn("text-xl font-semibold", tone)}>{value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

function FindingsTab({ audit }: { audit: AuditDetail }) {
  const [filter, setFilter] = useState<FindingFilter>({ status: "all", severity: "all", q: "" });
  const [expandAll, setExpandAll] = useState<boolean | undefined>(undefined);
  const counts = useMemo(() => countByStatus(audit.findings), [audit.findings]);
  const shown = useMemo(() => filterFindings(audit.findings, filter), [audit.findings, filter]);
  const statuses: (FindingStatus | "all")[] = ["all", "fail", "unknown", "pass", "not_applicable"];
  const isFiltered = filter.status !== "all" || filter.severity !== "all" || filter.q !== "";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {statuses.map((s) => (
            <button key={s} onClick={() => setFilter({ ...filter, status: s })} aria-pressed={filter.status === s}
              className={cn("rounded-full border px-3 py-1 text-xs font-medium transition-colors", filter.status === s ? "border-ink bg-ink text-white shadow-sm" : "border-line bg-paper text-ink hover:bg-mist")}>
              {s === "all" ? "All" : STATUS_LABEL[s]} <span className="opacity-70 ml-1">{counts[s]}</span>
            </button>
          ))}
          <select aria-label="Severity" className={cn(inputCls, "w-auto text-xs py-1")} value={filter.severity} onChange={(e) => setFilter({ ...filter, severity: e.target.value as FindingFilter["severity"] })}>
            <option value="all">Any severity</option>
            {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input aria-label="Search findings" className={cn(inputCls, "w-44 text-xs py-1")} placeholder="Search title or ID..." value={filter.q} onChange={(e) => setFilter({ ...filter, q: e.target.value })} />
          {isFiltered && (
            <button onClick={() => setFilter({ status: "all", severity: "all", q: "" })} className="text-xs text-signal underline hover:text-signal-dark">
              Reset filters
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setExpandAll((v) => (v === true ? false : true))}
            className="rounded border border-line bg-paper px-2.5 py-1 text-xs font-medium text-muted hover:bg-mist hover:text-ink transition-colors"
          >
            {expandAll === true ? "Collapse all" : "Expand all"}
          </button>
        </div>
      </div>
      {shown.length === 0 ? <Empty>No findings match these filters.</Empty> : <div className="space-y-2.5">{shown.map((f) => <FindingCard key={`${f.id}-${expandAll}`} f={f} forceOpen={expandAll} />)}</div>}
      <p className="mt-4 text-xs text-muted">
        “Unverified” means the file did not provide enough evidence to decide. It is excluded from the score and never counted as compliant. Rule catalog v{audit.catalog_version}.
      </p>
    </div>
  );
}

function UnknownTab({ audit, reload }: { audit: AuditDetail; reload: () => void }) {
  const { isAdmin } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const unknown = audit.parse.result.unknown_commands;
  const mapped = new Set(audit.ai_mappings.map((m) => m.command_text));
  const unmapped = unknown.filter((u) => !mapped.has(u.text));

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      setResult(await generateMappings(audit.id));
      reload();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  if (unknown.length === 0) return <Empty>Every security-relevant command in scope was recognized by the parser.</Empty>;
  return (
    <div className="space-y-4">
      <Card>
        <p className="text-sm">
          The parser did not understand <b>{unknown.length}</b> security-relevant command{unknown.length > 1 ? "s" : ""}. They are not used as evidence.
          Suggestions below are <b>advisory</b>: they never change a finding, the score or the grade, and need a human to approve them.
        </p>
        {isAdmin && unmapped.length > 0 && <Button variant="primary" className="mt-3" disabled={busy} onClick={generate}>{busy ? "Working…" : `Suggest meanings (${unmapped.length})`}</Button>}
        {result && (
          <p className="mt-3 text-sm text-muted">
            {result.created} suggestion{result.created === 1 ? "" : "s"} created using {result.ai_used ? "the AI model" : "rule-based analysis"}
            {!result.ai_configured && " (no AI key configured)"}{result.ai_error && ` (AI call failed: ${result.ai_error}; fell back to rules)`}.
          </p>
        )}
        <div className="mt-2"><ErrorNote error={error} /></div>
      </Card>
      {unmapped.length > 0 && (
        <Card title="Not yet analyzed">
          <ul className="space-y-1">{unmapped.map((u, i) => <li key={i} className="font-mono text-xs"><span className="mr-2 text-muted">L{u.line_number}</span>{u.text}</li>)}</ul>
        </Card>
      )}
      <div className="space-y-3">{audit.ai_mappings.map((m) => <MappingCard key={m.id} m={m} onChanged={reload} />)}</div>
    </div>
  );
}

export default function AuditDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();
  const toast = useToast();
  const auditId = Number(id);
  const { data: audit, error, loading, reload } = useAsync(() => getAudit(auditId), [auditId]);
  const [tab, setTab] = useState<Tab>("findings");
  const [actionError, setActionError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (loading && !audit) return <Spinner />;
  if (error || !audit) return <ErrorNote error={error} />;

  async function pdf() {
    setBusy(true); setActionError(null);
    toast.info("Generating PDF audit report...");
    try {
      await downloadReport(audit!.id);
      toast.success("PDF report downloaded successfully");
    } catch (e) {
      setActionError(e);
      toast.error("Failed to generate PDF report");
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    if (!window.confirm(`Delete audit #${audit!.id} (${audit!.filename})? This cannot be undone.`)) return;
    try {
      await deleteAudit(audit!.id);
      toast.success("Audit deleted successfully");
      navigate("/audits");
    } catch (e) {
      setActionError(e);
      toast.error("Failed to delete audit");
    }
  }

  const sevTotal = SEVERITIES.reduce((n, s) => n + (audit.failed_by_severity[s] ?? 0), 0);
  const tabs: { key: Tab; label: string }[] = [
    { key: "findings", label: `Findings (${audit.findings.length})` },
    { key: "config", label: "Parsed configuration" },
    { key: "unknown", label: `Unrecognized commands (${audit.parse.result.unknown_commands.length})` },
  ];

  return (
    <>
      <p className="mb-2 text-sm"><Link to="/audits" className="text-signal underline">← History</Link></p>
      <PageHeader
        title={audit.hostname ?? audit.filename}
        subtitle={<>{audit.filename} · {vendorLabel(audit.vendor)} · {audit.line_count} lines · audited {formatDate(audit.created_at)}{audit.created_by ? ` by ${audit.created_by}` : ""}</>}
        actions={<>
          <Button variant="primary" disabled={busy} onClick={pdf}>{busy ? "Preparing…" : "Download PDF report"}</Button>
          {isAdmin && <Button variant="danger" onClick={remove}>Delete</Button>}
        </>}
      />
      <ErrorNote error={actionError} />

      <Card className="mb-6">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          <ScoreRing score={audit.score} grade={audit.grade} />
          <div className="min-w-0 flex-1 space-y-4">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="Passed" value={audit.passed} tone="text-pass" />
              <Stat label="Failed" value={audit.failed} tone="text-crit" />
              <Stat label="Unverified" value={audit.unknown} tone="text-med" />
              <Stat label="Not applicable" value={audit.not_applicable} tone="text-unk" />
            </div>
            {sevTotal > 0 && <div><div className="mb-1 text-xs font-medium text-muted">Failed checks by severity</div><SeverityBar counts={audit.failed_by_severity} /></div>}
            <p className="text-sm text-muted">
              Highest failed severity: <b className="text-ink">{audit.risk_level}</b> · Evidence coverage: <b className="text-ink">{audit.coverage === null ? "N/A" : `${Math.round(audit.coverage)}%`}</b>
              {audit.grade === "D" && audit.failed_by_severity.critical ? <Chip tone="bg-crit-wash text-crit"> grade capped by a critical failure</Chip> : null}
            </p>
          </div>
        </div>
      </Card>

      <div role="tablist" className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
        {tabs.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}
            className={cn("-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm", tab === t.key ? "border-signal font-medium text-ink" : "border-transparent text-muted hover:text-ink")}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "findings" && <FindingsTab audit={audit} />}
      {tab === "config" && <ParsedConfig data={audit.parse} />}
      {tab === "unknown" && <UnknownTab audit={audit} reload={reload} />}
    </>
  );
}
