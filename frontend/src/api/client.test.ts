import { describe, expect, it } from "vitest";
import { ApiError, toApiError } from "./client";

const res = (status: number, body: unknown) => new Response(typeof body === "string" ? body : JSON.stringify(body), { status });

describe("toApiError", () => {
  it("reads the backend error envelope", async () => {
    const e = await toApiError(res(422, { error: { code: "vendor_mismatch", message: "Mismatch", details: {} } }));
    expect(e).toBeInstanceOf(ApiError);
    expect([e.code, e.message, e.status]).toEqual(["vendor_mismatch", "Mismatch", 422]);
  });
  it("handles FastAPI validation errors without leaking details", async () => {
    const e = await toApiError(res(422, { detail: [{ loc: ["body", "x"], msg: "bad" }] }));
    expect(e.code).toBe("invalid_request");
    expect(e.message).not.toContain("bad");
  });
  it("tolerates non-JSON bodies", async () => {
    const e = await toApiError(res(502, "<html>Bad gateway</html>"));
    expect([e.code, e.status]).toEqual(["http_error", 502]);
  });
});
