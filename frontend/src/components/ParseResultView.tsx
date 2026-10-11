import { countSettings, formatBytes, formatValue, humanize, UNKNOWN_REASON_LABEL } from "../lib/format";
import type { ConfigParseResponse, Evidence, Section, Setting } from "../types";

const SECTIONS: { key: "management" | "authentication" | "logging" | "ntp" | "snmp"; title: string }[] = [
  { key: "management", title: "Management access" },
  { key: "authentication", title: "Authentication" },
  { key: "logging", title: "Logging" },
  { key: "ntp", title: "NTP" },
  { key: "snmp", title: "SNMP" },
];

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return null;
  return (
    <ul className="mt-1 space-y-0.5">
      {evidence.map((e, i) => (
        <li key={i} className="font-mono text-xs text-slate-600">
          <span className="mr-2 text-slate-400">{e.line_number ? `L${e.line_number}` : "—"}</span>
          {e.text}
        </li>
      ))}
    </ul>
  );
}

function SettingRow({ name, s }: { name: string; s: Setting }) {
  const known = s.state === "known";
  return (
    <tr className="align-top">
      <td className="py-2 pr-4 text-sm font-medium">{humanize(name)}</td>
      <td className="py-2 pr-4">
        {known ? (
          <span className="rounded bg-emerald-50 px-2 py-0.5 text-sm text-emerald-800">{formatValue(s.value)}</span>
        ) : (
          <span className="rounded bg-amber-50 px-2 py-0.5 text-sm text-amber-800">
            Unknown · {s.unknown_reason ? UNKNOWN_REASON_LABEL[s.unknown_reason] : ""}
          </span>
        )}
      </td>
      <td className="py-2 text-sm">
        <EvidenceList evidence={s.evidence} />
        {s.note && <p className="mt-1 text-xs italic text-slate-500">{s.note}</p>}
      </td>
    </tr>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-3 text-base font-semibold">{title}</h3>
      {children}
    </section>
  );
}

export default function ParseResultView({ data }: { data: ConfigParseResponse }) {
  const { result, file, detection } = data;
  const cfg = result.config;
  const counts = countSettings(SECTIONS.map((s) => cfg[s.key] as Section));
  const allWarnings = [...data.warnings, ...result.warnings];

  return (
    <div className="space-y-5">
      <Card title="Analysis summary">
        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt className="text-slate-500">File</dt><dd className="break-all font-medium">{file.filename}</dd><dd className="text-xs text-slate-500">{formatBytes(file.size_bytes)} · {file.line_count} lines</dd></div>
          <div><dt className="text-slate-500">Vendor</dt><dd className="font-medium">{data.vendor_used}</dd><dd className="text-xs text-slate-500">requested: {data.requested_vendor} · detected: {detection.detected_vendor ?? "none"} ({detection.confidence})</dd></div>
          <div><dt className="text-slate-500">Hostname</dt><dd className="font-medium">{formatValue(cfg.hostname.value)}</dd><dd className="text-xs text-slate-500">parser {result.parser_name} v{result.parser_version} · schema {result.schema_version}</dd></div>
          <div><dt className="text-slate-500">Settings extracted</dt><dd className="font-medium">{counts.known} known · {counts.unknown} unknown</dd><dd className="text-xs text-slate-500">unknown = not proven, never assumed</dd></div>
        </dl>
        <p className="mt-3 break-all font-mono text-xs text-slate-400">sha256 {file.sha256}</p>
      </Card>

      {allWarnings.length > 0 && (
        <Card title={`Warnings (${allWarnings.length})`}>
          <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
            {allWarnings.map((w, i) => (
              <li key={i}>{w.message}{w.line_number ? ` (line ${w.line_number})` : ""}</li>
            ))}
          </ul>
        </Card>
      )}

      {SECTIONS.map(({ key, title }) => (
        <Card key={key} title={title}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-left">
              <tbody className="divide-y divide-slate-100">
                {Object.entries(cfg[key] as Section).map(([name, s]) => (
                  <SettingRow key={name} name={name} s={s} />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}

      <Card title={`Detected weak settings (${cfg.detected_weak_settings.length})`}>
        {cfg.detected_weak_settings.length === 0 ? (
          <p className="text-sm text-slate-600">
            None detected. This does not prove the configuration is secure; only detectable patterns are checked.
          </p>
        ) : (
          <ul className="space-y-3">
            {cfg.detected_weak_settings.map((w) => (
              <li key={w.identifier} className="rounded-md border border-red-100 bg-red-50 p-3">
                <p className="text-sm font-medium text-red-900">{w.identifier} <span className="font-normal text-red-600">· {w.category}</span></p>
                <p className="text-sm text-red-800">{w.description}</p>
                <EvidenceList evidence={w.evidence} />
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title={`Unrecognized security-relevant commands (${result.unknown_commands.length})`}>
        {result.unknown_commands.length === 0 ? (
          <p className="text-sm text-slate-600">Every security-relevant command in scope was recognized.</p>
        ) : (
          <>
            <p className="mb-2 text-sm text-slate-600">These were not understood by the parser and are not used as evidence. Mapping them arrives in Phase 5.</p>
            <ul className="space-y-1">
              {result.unknown_commands.map((u, i) => (
                <li key={i} className="font-mono text-xs text-slate-700"><span className="mr-2 text-slate-400">L{u.line_number}</span>{u.text}</li>
              ))}
            </ul>
          </>
        )}
      </Card>
    </div>
  );
}
