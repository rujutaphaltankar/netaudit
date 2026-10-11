import { describe, expect, it } from "vitest";
import { countSettings, formatBytes, formatValue, humanize } from "./format";
import type { Setting } from "../types";

const known = (value: unknown): Setting => ({ state: "known", value, unknown_reason: null, evidence: [], note: null });
const unknown: Setting = { state: "unknown", value: null, unknown_reason: "not_found", evidence: [], note: null };

describe("formatValue", () => {
  it("formats booleans, lists and empties", () => {
    expect(formatValue(true)).toBe("Yes");
    expect(formatValue(false)).toBe("No");
    expect(formatValue(["a", "b"])).toBe("a, b");
    expect(formatValue([])).toBe("none");
    expect(formatValue(null)).toBe("—");
    expect(formatValue(0)).toBe("0");
  });
});

describe("countSettings", () => {
  it("counts known and unknown separately and never treats unknown as known", () => {
    expect(countSettings([{ a: known(true), b: unknown }, { c: known([]) }])).toEqual({ known: 2, unknown: 1 });
  });
});

describe("misc helpers", () => {
  it("humanizes keys and formats sizes", () => {
    expect(humanize("ssh_enabled")).toBe("Ssh enabled");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
  });
});
