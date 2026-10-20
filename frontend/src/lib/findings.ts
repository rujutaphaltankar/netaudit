import type { Finding, FindingStatus, Severity } from "../types";

export interface FindingFilter {
  status: FindingStatus | "all";
  severity: Severity | "all";
  q: string;
}

export function filterFindings(findings: Finding[], f: FindingFilter): Finding[] {
  const q = f.q.trim().toLowerCase();
  return findings.filter(
    (x) =>
      (f.status === "all" || x.status === f.status) &&
      (f.severity === "all" || x.severity === f.severity) &&
      (!q || `${x.rule_id} ${x.title} ${x.category} ${x.message}`.toLowerCase().includes(q)),
  );
}

export function countByStatus(findings: Finding[]): Record<FindingStatus | "all", number> {
  const out = { all: findings.length, fail: 0, pass: 0, unknown: 0, not_applicable: 0 };
  for (const x of findings) out[x.status]++;
  return out;
}
