import type {
  AIMapping, AuditComparison, AuditDetail, AuditPage, ConfigParseResponse, DashboardStats, GenerateResult,
  Health, LoginResponse, RuleCatalog, Role, User, VendorInfo,
} from "../types";

export const API_BASE: string = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
const V1 = `${API_BASE}/api/v1`;
const TOKEN_KEY = "netaudit.token";
export const UNAUTHORIZED_EVENT = "netaudit:unauthorized";

// sessionStorage: the token disappears when the tab closes. (An httpOnly cookie would be stronger; see docs/SECURITY.md.)
export const getToken = (): string | null => sessionStorage.getItem(TOKEN_KEY);
export const setToken = (t: string | null) => (t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY));

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
    if (Array.isArray(body?.detail)) return new ApiError("invalid_request", "The request was not valid. Check the values you entered.", res.status);
  } catch {
    /* fall through */
  }
  return new ApiError("http_error", `The server responded with status ${res.status}.`, res.status);
}

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${V1}${path}`, { ...init, headers: { ...authHeaders(), ...(init.headers ?? {}) } });
  } catch {
    throw new ApiError("network_error", `Cannot reach the backend at ${API_BASE}. Is it running?`, 0);
  }
  if (res.status === 401 && getToken()) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  if (!res.ok) throw await toApiError(res);
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await send(path, init);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// public
export const getHealth = () => request<Health>("/health");
export const getVendors = () => request<VendorInfo[]>("/vendors");
export const login = (username: string, password: string) => request<LoginResponse>("/auth/login", json("POST", { username, password }));

// authenticated
export const getMe = () => request<User>("/auth/me");
export const getStats = () => request<DashboardStats>("/audits/stats");
export const getRules = () => request<RuleCatalog>("/rules");

export function listAudits(p: { page: number; pageSize: number; vendor?: string; q?: string }) {
  const qs = new URLSearchParams({ page: String(p.page), page_size: String(p.pageSize) });
  if (p.vendor) qs.set("vendor", p.vendor);
  if (p.q) qs.set("q", p.q);
  return request<AuditPage>(`/audits?${qs}`);
}
export const getAudit = (id: number) => request<AuditDetail>(`/audits/${id}`);
export const deleteAudit = (id: number) => request<void>(`/audits/${id}`, { method: "DELETE" });
export const compareAudits = (base: number, target: number) => request<AuditComparison>(`/audits/compare?base=${base}&target=${target}`);

export function createAudit(file: File, vendor: string, forceVendor: boolean) {
  const form = new FormData();
  form.append("file", file);
  form.append("vendor", vendor);
  form.append("force_vendor", String(forceVendor));
  return request<AuditDetail>("/audits", { method: "POST", body: form });
}

/** Stateless preview (nothing stored). */
export function parseConfig(file: File, vendor: string, forceVendor: boolean) {
  const form = new FormData();
  form.append("file", file);
  form.append("vendor", vendor);
  form.append("force_vendor", String(forceVendor));
  return request<ConfigParseResponse>("/configs/parse", { method: "POST", body: form });
}

export async function downloadReport(id: number): Promise<void> {
  const blob = await (await send(`/audits/${id}/report.pdf`)).blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `netaudit-report-${id}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// AI review
export const generateMappings = (auditId: number) => request<GenerateResult>(`/audits/${auditId}/ai-mappings/generate`, { method: "POST" });
export const listMappings = (status?: string) => request<AIMapping[]>(`/ai-mappings${status ? `?status=${status}` : ""}`);
export const reviewMapping = (id: number, decision: "approved" | "rejected", note?: string) =>
  request<AIMapping>(`/ai-mappings/${id}/review`, json("POST", { decision, note: note || null }));

// users (admin)
export const listUsers = () => request<User[]>("/users");
export const createUser = (username: string, password: string, role: Role) => request<User>("/users", json("POST", { username, password, role }));
export const updateUser = (id: number, patch: { is_active?: boolean; role?: Role }) => request<User>(`/users/${id}`, json("PATCH", patch));
