import { Card } from "./ui";
import { countSettings, formatValue, humanize, UNKNOWN_REASON_LABEL } from "../lib/format";
import type { ConfigParseResponse, Evidence, Section, Setting } from "../types";

const SECTIONS = [
  { key: "management", title: "Management access" },
  { key: "authentication", title: "Authentication" },
  { key: "logging", title: "Logging" },
  { key: "ntp", title: "NTP" },
  { key: "snmp", title: "SNMP" },
] as const;

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return null;
  return (
    <ul className="space-y-0.5">
      {evidence.map((e, i) => (
        <li key={i} className="font-mono text-xs text-muted"><span className="mr-2 opacity-60">{e.line_number ? `L${e.line_number}` : "—"}</span>{e.text}</li>
      ))}
    </ul>
  );
}

function Row({ name, s }: { name: string; s: Setting }) {
  const known = s.state === "known";
  return (
    <tr className="align-top">
      <td className="py-2 pr-4 text-sm font-medium text-ink">{humanize(name)}</td>
      <td className="py-2 pr-4">
        {known
          ? <span className="rounded bg-pass-wash px-2 py-0.5 text-sm text-pass">{formatValue(s.value)}</span>
          : <span className="rounded bg-med-wash px-2 py-0.5 text-sm text-med">Unknown · {s.unknown_reason ? UNKNOWN_REASON_LABEL[s.unknown_reason] : ""}</span>}
      </td>
      <td className="py-2"><EvidenceList evidence={s.evidence} />{s.note && <p className="mt-1 text-xs italic text-muted">{s.note}</p>}</td>
    </tr>
  );
}

export default function ParsedConfig({ data }: { data: ConfigParseResponse }) {
  const { result, detection } = data;
  const cfg = result.config;
  const counts = countSettings(SECTIONS.map((s) => cfg[s.key] as Section));
  const warnings = [...data.warnings, ...result.warnings];
  return (
    <div className="space-y-4">
      <Card title="How the file was read">
        <p className="text-sm">
          Parser <b>{result.parser_name}</b> v{result.parser_version} (schema {result.schema_version}). Vendor requested: {data.requested_vendor}; detected: {detection.detected_vendor ?? "none"} ({detection.confidence} confidence).
          Extracted <b>{counts.known}</b> known and <b>{counts.unknown}</b> unknown settings. Unknown means not proven, never assumed.
        </p>
        <p className="mt-2 break-all font-mono text-xs text-muted">sha256 {data.file.sha256}</p>
      </Card>
      {warnings.length > 0 && (
        <Card title={`Warnings (${warnings.length})`}>
          <ul className="list-disc space-y-1 pl-5 text-sm text-med">{warnings.map((w, i) => <li key={i}>{w.message}{w.line_number ? ` (line ${w.line_number})` : ""}</li>)}</ul>
        </Card>
      )}
      {SECTIONS.map(({ key, title }) => (
        <Card key={key} title={title}>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-left"><tbody className="divide-y divide-line">
              {Object.entries(cfg[key] as Section).map(([name, s]) => <Row key={name} name={name} s={s} />)}
            </tbody></table>
          </div>
        </Card>
      ))}
    </div>
  );
}
