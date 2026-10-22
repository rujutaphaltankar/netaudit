import { useMemo, useState } from "react";
import { useToast } from "../context/ToastContext";
import { countSettings, formatValue, humanize, UNKNOWN_REASON_LABEL } from "../lib/format";
import type { ConfigParseResponse, Evidence, Section, Setting } from "../types";
import { Button, Card, inputCls } from "./ui";

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
        <li key={i} className="font-mono text-xs text-muted">
          <span className="mr-2 opacity-60">{e.line_number ? `L${e.line_number}` : "—"}</span>
          {e.text}
        </li>
      ))}
    </ul>
  );
}

function Row({ name, s }: { name: string; s: Setting }) {
  const known = s.state === "known";
  return (
    <tr className="align-top hover:bg-mist/40 transition-colors">
      <td className="py-2.5 pr-4 text-sm font-medium text-ink">{humanize(name)}</td>
      <td className="py-2.5 pr-4">
        {known ? (
          <span className="rounded bg-pass-wash px-2 py-0.5 text-xs font-semibold text-pass">
            {formatValue(s.value)}
          </span>
        ) : (
          <span className="rounded bg-med-wash px-2 py-0.5 text-xs font-medium text-med">
            Unknown · {s.unknown_reason ? UNKNOWN_REASON_LABEL[s.unknown_reason] : ""}
          </span>
        )}
      </td>
      <td className="py-2.5">
        <EvidenceList evidence={s.evidence} />
        {s.note && <p className="mt-1 text-xs italic text-muted">{s.note}</p>}
      </td>
    </tr>
  );
}

export default function ParsedConfig({ data }: { data: ConfigParseResponse }) {
  const { result, detection } = data;
  const cfg = result.config;
  const counts = countSettings(SECTIONS.map((s) => cfg[s.key] as Section));
  const warnings = [...data.warnings, ...result.warnings];
  const [filter, setFilter] = useState("");
  const toast = useToast();

  const filteredSections = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) {
      return SECTIONS.map((s) => ({
        ...s,
        entries: Object.entries(cfg[s.key] as Section),
      }));
    }
    return SECTIONS.map((s) => ({
      ...s,
      entries: Object.entries(cfg[s.key] as Section).filter(
        ([name, setting]) =>
          name.toLowerCase().includes(q) ||
          humanize(name).toLowerCase().includes(q) ||
          String(setting.value).toLowerCase().includes(q) ||
          setting.evidence.some((e) => e.text.toLowerCase().includes(q))
      ),
    })).filter((s) => s.entries.length > 0);
  }, [cfg, filter]);

  function copyJson() {
    try {
      navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      toast.success("Normalized parsed configuration JSON copied");
    } catch {
      toast.error("Failed to copy JSON");
    }
  }

  return (
    <div className="space-y-4">
      <Card
        title="Normalized configuration analysis"
        action={
          <Button variant="secondary" onClick={copyJson} className="text-xs">
            📋 Copy JSON schema
          </Button>
        }
      >
        <p className="text-sm text-body leading-relaxed">
          Parser <b className="text-ink">{result.parser_name}</b> v{result.parser_version} (schema {result.schema_version}). Vendor requested:{" "}
          <span className="font-mono text-xs">{data.requested_vendor}</span>; detected:{" "}
          <b className="text-ink">{detection.detected_vendor ?? "none"}</b> ({detection.confidence} confidence).
          Extracted <b className="text-pass">{counts.known}</b> known and <b className="text-med">{counts.unknown}</b> unknown settings.
        </p>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line/60 pt-3">
          <p className="break-all font-mono text-xs text-muted">SHA-256: {data.file.sha256}</p>
          <input
            type="search"
            aria-label="Filter configuration settings"
            placeholder="Search parsed settings..."
            className={`${inputCls} w-56 text-xs`}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
      </Card>

      {warnings.length > 0 && (
        <Card title={`Parser warnings (${warnings.length})`}>
          <ul className="list-disc space-y-1 pl-5 text-sm text-med">
            {warnings.map((w, i) => (
              <li key={i}>
                {w.message}
                {w.line_number ? ` (line ${w.line_number})` : ""}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {filteredSections.length === 0 ? (
        <Card>
          <p className="text-sm text-muted text-center py-4">No configuration settings match "{filter}".</p>
        </Card>
      ) : (
        filteredSections.map(({ key, title, entries }) => (
          <Card key={key} title={`${title} (${entries.length})`}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[32rem] text-left">
                <tbody className="divide-y divide-line">
                  {entries.map(([name, s]) => (
                    <Row key={name} name={name} s={s} />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
