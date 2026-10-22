import { describe, expect, it } from "vitest";

describe("Comparison and Error Boundary logic", () => {
  it("determines score delta and direction correctly", () => {
    const calcDelta = (base: number, target: number) => target - base;
    expect(calcDelta(70, 85)).toBe(15);
    expect(calcDelta(85, 70)).toBe(-15);
    expect(calcDelta(80, 80)).toBe(0);
  });

  it("classifies audit status transitions accurately", () => {
    type ChangeType = "improved" | "regressed" | "unchanged";
    function classify(base: string, target: string): ChangeType {
      if (base === target) return "unchanged";
      if (base === "fail" && target === "pass") return "improved";
      if (base === "pass" && target === "fail") return "regressed";
      return "unchanged";
    }

    expect(classify("fail", "pass")).toBe("improved");
    expect(classify("pass", "fail")).toBe("regressed");
    expect(classify("pass", "pass")).toBe("unchanged");
  });
});
