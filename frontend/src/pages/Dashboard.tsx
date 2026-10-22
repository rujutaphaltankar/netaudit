import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { getStats } from "../api/client";
import { Card, Empty, ErrorNote, PageHeader, SeverityBadge, Spinner, useAsync } from "../components/ui";
import { SEVERITIES, SEVERITY_HEX, formatDate, formatDay, formatScore, gradeHex, vendorLabel } from "../lib/ui";

function Tile({
  label,
  value,
  hint,
  to,
  tone = "signal",
  icon,
}: {
  label: string;
  value: string;
  hint?: string;
  to?: string;
  tone?: "signal" | "crit" | "pass" | "neutral";
  icon?: string;
}) {
  const toneClasses = {
    signal: "hover:border-signal/70 bg-gradient-to-br from-paper via-paper to-signal-wash/30",
    crit: "hover:border-crit/70 bg-gradient-to-br from-paper via-paper to-crit-wash/30",
    pass: "hover:border-pass/70 bg-gradient-to-br from-paper via-paper to-pass-wash/30",
    neutral: "hover:border-ink/50 bg-paper",
  }[tone];

  const body = (
    <div className={`relative overflow-hidden rounded-xl border border-line p-5 shadow-xs transition-all hover:shadow-md ${toneClasses}`}>
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</div>
        {icon && <span className="text-base opacity-75">{icon}</span>}
      </div>
      <div className="mt-2 text-3xl font-bold tracking-tight text-ink">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted truncate">{hint}</div>}
    </div>
  );
  return to ? <Link to={to} className="block transition-transform active:scale-[0.99]">{body}</Link> : body;
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
          No audits yet.{" "}
          <Link to="/audits/new" className="font-medium text-signal underline">
            Upload a configuration
          </Link>{" "}
          to see scores, findings and trends here.
        </Empty>
      </>
    );
  }

  const trend = s.score_trend.map((p) => ({ label: `${formatDay(p.created_at)} #${p.id}`, score: p.score, file: p.filename }));
  const sev = SEVERITIES.map((k) => ({ name: k, count: s.failed_by_severity[k] ?? 0 }));
  const critHigh = (s.failed_by_severity.critical ?? 0) + (s.failed_by_severity.high ?? 0);

  const postureTone = critHigh === 0 ? "text-pass" : critHigh <= 3 ? "text-high" : "text-crit";
  const postureLabel = critHigh === 0 ? "Optimal Security" : critHigh <= 3 ? "Action Required" : "High Risk Exposure";

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Real-time security posture across all audited network devices and configurations."
        actions={
          <Link
            to="/audits/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-signal px-3.5 py-2 text-xs font-semibold text-white shadow-xs hover:bg-signal-dark transition-colors"
          >
            <span>+</span> Run New Audit
          </Link>
        }
      />

      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-paper px-5 py-3.5 shadow-xs">
        <div className="flex items-center gap-3">
          <span className="relative flex h-3 w-3">
            <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${critHigh === 0 ? "bg-pass" : "bg-crit"}`} />
            <span className={`relative inline-flex h-3 w-3 rounded-full ${critHigh === 0 ? "bg-pass" : "bg-crit"}`} />
          </span>
          <div>
            <span className="text-xs text-muted">Overall posture: </span>
            <span className={`text-xs font-bold uppercase tracking-wider ${postureTone}`}>{postureLabel}</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted">
          <span>{s.total_audits} total audit{s.total_audits === 1 ? "" : "s"}</span>
          <span>·</span>
          <span>Avg score: <b className="text-ink">{formatScore(s.average_score)}/100</b></span>
          <span>·</span>
          <span>Catalog: <b className="text-ink">19 compliance rules</b></span>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Tile
          label="Audits Analyzed"
          value={String(s.total_audits)}
          hint={Object.entries(s.by_vendor).map(([v, n]) => `${n} ${vendorLabel(v)}`).join(" · ")}
          to="/audits"
          tone="neutral"
          icon="📊"
        />
        <Tile
          label="Average Score"
          value={formatScore(s.average_score)}
          hint="Weighted compliance average (0–100)"
          tone={s.average_score && s.average_score >= 80 ? "pass" : "signal"}
          icon="🛡️"
        />
        <Tile
          label="Critical & High Risks"
          value={String(critHigh)}
          hint="Failures requiring immediate action"
          tone={critHigh > 0 ? "crit" : "pass"}
          icon="⚠️"
        />
        <Tile
          label="AI Review Queue"
          value={String(s.pending_ai_reviews)}
          hint="Advisory suggestions awaiting approval"
          to="/ai-review"
          tone="signal"
          icon="✨"
        />
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-5">
        <Card title="Security Score Trend" className="lg:col-span-3">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend} margin={{ top: 12, right: 12, bottom: 0, left: -18 }}>
                <CartesianGrid stroke="#e3e9ed" vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={{ stroke: "#d5dde3" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#10202c",
                    borderColor: "#2b3a46",
                    borderRadius: "6px",
                    color: "#ffffff",
                    fontSize: "12px",
                  }}
                  itemStyle={{ color: "#cfe9eb" }}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#0e7c86"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "#0e7c86", strokeWidth: 2, stroke: "#ffffff" }}
                  activeDot={{ r: 6, fill: "#0e7c86" }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Failed Checks by Severity" className="lg:col-span-2">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sev} margin={{ top: 12, right: 8, bottom: 0, left: -22 }}>
                <CartesianGrid stroke="#e3e9ed" vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={{ stroke: "#d5dde3" }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#5b6b78" }} tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ fill: "#edf1f4" }}
                  contentStyle={{
                    backgroundColor: "#10202c",
                    borderColor: "#2b3a46",
                    borderRadius: "6px",
                    color: "#ffffff",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {sev.map((e) => (
                    <Cell key={e.name} fill={SEVERITY_HEX[e.name]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <Card title="Top Failing Rules">
          {s.top_failing_rules.length === 0 ? (
            <p className="text-sm text-muted py-3">No failed checks recorded.</p>
          ) : (
            <ul className="divide-y divide-line">
              {s.top_failing_rules.map((r) => (
                <li key={r.rule_id} className="flex items-center gap-3 py-2.5 text-sm hover:bg-mist/30 transition-colors rounded px-1">
                  <span className="w-10 shrink-0 text-right font-bold text-crit">{r.count}×</span>
                  <span className="min-w-0 flex-1 truncate">
                    <span className="font-mono text-xs text-muted mr-1.5">{r.rule_id}</span>
                    <span className="font-medium text-ink">{r.title}</span>
                  </span>
                  <SeverityBadge severity={r.severity} />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card
          title="Recent Audits"
          action={
            <Link to="/audits" className="text-xs font-semibold text-signal hover:underline">
              View All Audits →
            </Link>
          }
        >
          <ul className="divide-y divide-line">
            {s.recent.map((a) => (
              <li key={a.id}>
                <Link to={`/audits/${a.id}`} className="flex items-center gap-3 py-2.5 text-sm hover:bg-mist/30 transition-colors rounded px-1">
                  <span
                    className="grid size-9 shrink-0 place-items-center rounded-lg font-bold text-white shadow-xs"
                    style={{ background: gradeHex(a.grade) }}
                  >
                    {a.grade}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold text-ink hover:text-signal">{a.hostname ?? a.filename}</span>
                    <span className="block text-xs text-muted">
                      {vendorLabel(a.vendor)} · {formatDate(a.created_at)}
                    </span>
                  </span>
                  <span className="font-mono font-bold text-ink">{formatScore(a.score)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
