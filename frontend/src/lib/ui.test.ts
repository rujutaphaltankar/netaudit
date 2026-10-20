import { describe, expect, it } from "vitest";
import { cn, formatScore, gradeHex, ringGeometry, vendorLabel } from "./ui";

describe("ringGeometry", () => {
  it("fills proportionally to the score and clamps out-of-range values", () => {
    const full = ringGeometry(100);
    expect(full.offset).toBeCloseTo(0);
    expect(ringGeometry(0).offset).toBeCloseTo(full.circumference);
    expect(ringGeometry(50).offset).toBeCloseTo(full.circumference / 2);
    expect(ringGeometry(250).offset).toBeCloseTo(0);
    expect(ringGeometry(-5).offset).toBeCloseTo(full.circumference);
  });
  it("draws an empty ring when there is no score", () => {
    expect(ringGeometry(null).offset).toBeCloseTo(ringGeometry(0).offset);
  });
});

describe("display helpers", () => {
  it("formats scores, grades and vendors", () => {
    expect(formatScore(97.6)).toBe("98");
    expect(formatScore(null)).toBe("N/A");
    expect(gradeHex("F")).not.toBe(gradeHex("A"));
    expect(gradeHex("???")).toBe(gradeHex("N/A"));
    expect(vendorLabel("cisco_ios")).toBe("Cisco IOS");
    expect(vendorLabel("other")).toBe("other");
    expect(cn("a", false, null, "b")).toBe("a b");
  });
});
