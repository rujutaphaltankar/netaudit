import type { ConfigParseResponse, Health, VendorInfo } from "../types";

export const API_BASE: string = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const V1 = `${API_BASE}/api/v1`;

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Convert any failed response into an ApiError, tolerating non-JSON bodies. */
export async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    if (body?.error?.code) return new ApiError(body.error.code, body.error.message, res.status);
    if (Array.isArray(body?.detail)) return new ApiError("invalid_request", "The request was not valid. Check the selected file and options.", res.status);
  } catch {
    /* fall through */
  }
  return new ApiError("http_error", `The server responded with status ${res.status}.`, res.status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${V1}${path}`, init);
  } catch {
    throw new ApiError("network_error", `Cannot reach the backend at ${API_BASE}. Is it running?`, 0);
  }
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as T;
}

export const getHealth = () => request<Health>("/health");
export const getVendors = () => request<VendorInfo[]>("/vendors");

export function parseConfig(file: File, vendor: string, forceVendor: boolean) {
  const form = new FormData();
  form.append("file", file);
  form.append("vendor", vendor);
  form.append("force_vendor", String(forceVendor));
  return request<ConfigParseResponse>("/configs/parse", { method: "POST", body: form });
}
