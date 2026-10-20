import { describe, expect, it } from "vitest";
import { countByStatus, filterFindings } from "./findings";
import type { Finding } from "../types";

const f = (over: Partial<Finding>): Finding => ({
  id: 1, rule_id: "NA-X-001", title: "Telnet disabled", category: "Management Access", severity: "high", status: "fail",
  message: "Telnet is enabled", observed: null, unknown_reason: null, evidence: [], remediation: null, references: [], ...over,
});
const data = [
  f({ id: 1 }),
  f({ id: 2, rule_id: "NA-LOG-001", title: "Remote logging", category: "Logging", severity: "medium", status: "unknown", message: "no evidence" }),
  f({ id: 3, rule_id: "NA-NTP-001", title: "NTP configured", category: "Time", severity: "low", status: "pass" }),
];

describe("filterFindings", () => {
  it("filters by status, severity and free text", () => {
    expect(filterFindings(data, { status: "all", severity: "all", q: "" })).toHaveLength(3);
    expect(filterFindings(data, { status: "fail", severity: "all", q: "" }).map((x) => x.id)).toEqual([1]);
    expect(filterFindings(data, { status: "all", severity: "low", q: "" }).map((x) => x.id)).toEqual([3]);
    expect(filterFindings(data, { status: "all", severity: "all", q: " LOGGING " }).map((x) => x.id)).toEqual([2]);
    expect(filterFindings(data, { status: "pass", severity: "high", q: "" })).toEqual([]);
  });
});

describe("countByStatus", () => {
  it("keeps unverified findings separate from passes", () => {
    expect(countByStatus(data)).toEqual({ all: 3, fail: 1, pass: 1, unknown: 1, not_applicable: 0 });
  });
});
