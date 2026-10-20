import type { FindingStatus, Severity } from "../types";

export const cn = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

export const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

export const SEVERITY_STYLE: Record<Severity, string> = {
  critical: "bg-crit-wash text-crit",
  high: "bg-high-wash text-high",
  medium: "bg-med-wash text-med",
  low: "bg-low-wash text-low",
};
export const SEVERITY_HEX: Record<Severity, string> = { critical: "#9f1239", high: "#b84208", medium: "#c98a00", low: "#1d4ed8" };

export const STATUS_STYLE: Record<FindingStatus, string> = {
  fail: "bg-crit-wash text-crit",
  pass: "bg-pass-wash text-pass",
  unknown: "bg-med-wash text-med",
  not_applicable: "bg-unk-wash text-unk",
};
export const STATUS_LABEL: Record<FindingStatus, string> = { fail: "Fail", pass: "Pass", unknown: "Unverified", not_applicable: "N/A" };

export const VENDOR_LABEL: Record<string, string> = { cisco_ios: "Cisco IOS", juniper_junos: "Juniper Junos" };
export const vendorLabel = (v: string) => VENDOR_LABEL[v] ?? v;

export const GRADE_HEX: Record<string, string> = { A: "#137333", B: "#4d7c0f", C: "#b7791f", D: "#c2410c", F: "#b91c1c", "N/A": "#5b6b78" };
export const gradeHex = (g: string) => GRADE_HEX[g] ?? GRADE_HEX["N/A"];

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
export const formatDay = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
export const formatScore = (s: number | null) => (s === null ? "N/A" : String(Math.round(s)));

/** Geometry of the score ring. Pure so it can be unit-tested. */
export function ringGeometry(score: number | null, radius = 54) {
  const circumference = 2 * Math.PI * radius;
  const pct = score === null ? 0 : Math.max(0, Math.min(100, score));
  return { circumference, offset: circumference * (1 - pct / 100) };
}
