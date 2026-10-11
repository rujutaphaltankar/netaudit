import type { Section, Setting } from "../types";

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "none";
  return String(value);
}

export const UNKNOWN_REASON_LABEL: Record<string, string> = {
  not_found: "Not found in file",
  ambiguous: "Ambiguous / default-dependent",
  unsupported: "Not modelled for this vendor",
  unrecognized: "Present but not recognized",
};

export function humanize(key: string): string {
  const s = key.replace(/_/g, " ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function countSettings(sections: Section[]): { known: number; unknown: number } {
  let known = 0;
  let unknown = 0;
  for (const section of sections) {
    for (const s of Object.values(section) as Setting[]) {
      if (s.state === "known") known++;
      else unknown++;
    }
  }
  return { known, unknown };
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
