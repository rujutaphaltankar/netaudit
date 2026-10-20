import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { getStats } from "../api/client";
import { Card, Empty, ErrorNote, PageHeader, SeverityBadge, Spinner, useAsync } from "../components/ui";
import { SEVERITIES, SEVERITY_HEX, formatDate, formatDay, formatScore, gradeHex, vendorLabel } from "../lib/ui";

function Tile({ label, value, hint, to }: { label: string; value: string; hint?: string; to?: string }) {
  const body = (
    <div className="rounded-lg border border-line bg-paper p-4 transition-colors hover:border-signal">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-1 text-3xl font-semibold text-ink">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

export default function Dashboard() {
  const { data: s, error, loading } = useAsync(getStats, []);
  if (loading) return <Spinner />;
  if (error || !s) return <ErrorNote error={error} />;

  if (s.total_audits === 0) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <Empty>
          No audits yet. <Link to="/audits/new" className="font-medium text-signal underline">Upload a configuration</Link> to see scores, findings and trends here.
        </Empty>
      </>
    );
  }

  const trend = s.score_trend.map((p) => ({ label: `${formatDay(p.created_at)} #${p.id}`, score: p.score, file: p.filename }));
  const sev = SEVERITIES.map((k) => ({ name: k, count: s.failed_by_severity[k] ?? 0 }));
  const critHigh = (s.failed_by_severity.critical ?? 0) + (s.failed_by_severity.high ?? 0);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Security posture across all audited configurations." />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Audits" value={String(s.total_audits)} hint={Object.entries(s.by_vendor).map(([v, n]) => `${n} ${vendorLabel(v)}`).join(" · ")} to="/audits" />
        <Tile label="Average score" value={formatScore(s.average_score)} hint="weighted, 0–100" />
        <Tile label="Critical + high failures" value={String(critHigh)} hint="across all audits" />
        <Tile label="Awaiting AI review" value={String(s.pending_ai_reviews)} hint="suggestions to approve" to="/ai-review" />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-5">
        <Card title="Score over time" className="lg:col-span-3">
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="#e3e9ed" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={{ stroke: "#d5dde3" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="score" stroke="#0e7c86" strokeWidth={2.5} dot={{ r: 4, fill: "#0e7c86" }} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Failed checks by severity" className="lg:col-span-2">
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sev} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
                <CartesianGrid stroke="#e3e9ed" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={{ stroke: "#d5dde3" }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "#edf1f4" }} />
                <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                  {sev.map((e) => <Cell key={e.name} fill={SEVERITY_HEX[e.name]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Most frequent failures">
          {s.top_failing_rules.length === 0 ? <p className="text-sm text-muted">No failed checks.</p> : (
            <ul className="divide-y divide-line">
              {s.top_failing_rules.map((r) => (
                <li key={r.rule_id} className="flex items-center gap-3 py-2 text-sm">
                  <span className="w-12 shrink-0 text-right font-semibold text-ink">{r.count}×</span>
                  <span className="min-w-0 flex-1"><span className="font-mono text-xs text-muted">{r.rule_id}</span> {r.title}</span>
                  <SeverityBadge severity={r.severity} />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Recent audits" action={<Link to="/audits" className="text-sm text-signal underline">All audits</Link>}>
          <ul className="divide-y divide-line">
            {s.recent.map((a) => (
              <li key={a.id}>
                <Link to={`/audits/${a.id}`} className="flex items-center gap-3 py-2.5 text-sm hover:text-signal">
                  <span className="grid size-9 shrink-0 place-items-center rounded-md font-semibold text-white" style={{ background: gradeHex(a.grade) }}>{a.grade}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-ink">{a.hostname ?? a.filename}</span>
                    <span className="block text-xs text-muted">{vendorLabel(a.vendor)} · {formatDate(a.created_at)}</span>
                  </span>
                  <span className="font-semibold text-ink">{formatScore(a.score)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
