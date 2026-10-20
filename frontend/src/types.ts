// Mirrors the backend API contract (backend/app/schemas). Keep in sync with /openapi.json.
export type Vendor = "cisco_ios" | "juniper_junos" | "palo_alto_panos" | "fortinet_fortios" | "arista_eos";

export interface Evidence {
  line_number: number | null;
  text: string;
  context: string | null;
}

export interface Setting {
  state: "known" | "unknown";
  value: unknown;
  unknown_reason: "not_found" | "ambiguous" | "unsupported" | "unrecognized" | null;
  evidence: Evidence[];
  note: string | null;
}

export type Section = Record<string, Setting>;

export interface DetectedWeakness {
  identifier: string;
  category: string;
  description: string;
  evidence: Evidence[];
}

export interface NormalizedConfig {
  schema_version: string;
  vendor: Vendor;
  hostname: Setting;
  management: Section;
  authentication: Section;
  logging: Section;
  ntp: Section;
  snmp: Section;
  detected_weak_settings: DetectedWeakness[];
}

export interface ParseWarning {
  code: string;
  message: string;
  line_number: number | null;
}

export interface UnknownCommand {
  vendor: Vendor;
  line_number: number | null;
  text: string;
  context: string | null;
}

export interface ParseResult {
  parser_name: string;
  parser_version: string;
  schema_version: string;
  vendor: Vendor;
  config: NormalizedConfig;
  warnings: ParseWarning[];
  unknown_commands: UnknownCommand[];
  line_count: number;
}

export interface VendorDetection {
  detected_vendor: Vendor | null;
  confidence: "high" | "medium" | "low" | "none";
  supported: boolean;
  signals: string[];
  scores: Record<string, number>;
}

export interface ConfigParseResponse {
  file: { filename: string; size_bytes: number; sha256: string; line_count: number; encoding: string };
  requested_vendor: string;
  vendor_used: Vendor;
  detection: VendorDetection;
  result: ParseResult;
  warnings: ParseWarning[];
}

export interface VendorInfo {
  id: Vendor;
  display_name: string;
  supported: boolean;
  parser_version: string | null;
}

export interface Health {
  status: string;
  app: string;
  version: string;
  environment: string;
  database: "not_configured" | "ok" | "unavailable";
  ai_assistance: "enabled" | "fallback_only";
  time: string;
}

// ---------------------------------------------------------------------------- Phase 4-9 additions
export type Severity = "critical" | "high" | "medium" | "low";
export type FindingStatus = "pass" | "fail" | "unknown" | "not_applicable";
export type Role = "admin" | "viewer";

export interface Reference {
  framework: string;
  control: string;
  title: string;
}

export interface Finding {
  id: number;
  rule_id: string;
  title: string;
  category: string;
  severity: Severity;
  status: FindingStatus;
  message: string;
  observed: string | null;
  unknown_reason: string | null;
  evidence: Evidence[];
  remediation: string | null;
  references: Reference[];
}

export interface AIMapping {
  id: number;
  audit_id: number;
  created_at: string;
  vendor: string;
  line_number: number | null;
  command_text: string;
  context: string | null;
  meaning: string;
  category: string;
  security_impact: "positive" | "neutral" | "negative" | "unknown";
  confidence: "low" | "medium" | "high";
  suggested_field: string | null;
  note: string | null;
  source: "ai" | "heuristic" | "reused";
  status: "pending" | "approved" | "rejected";
  reviewed_at: string | null;
  review_note: string | null;
  audit_filename: string | null;
}

export interface AuditItem {
  id: number;
  created_at: string;
  created_by: string | null;
  filename: string;
  sha256: string;
  vendor: string;
  hostname: string | null;
  score: number | null;
  grade: string;
  risk_level: string;
  coverage: number | null;
  passed: number;
  failed: number;
  unknown: number;
  not_applicable: number;
  failed_by_severity: Partial<Record<Severity, number>>;
}

export interface AuditDetail extends AuditItem {
  catalog_version: string;
  parser_version: string;
  line_count: number;
  size_bytes: number;
  findings: Finding[];
  parse: ConfigParseResponse;
  ai_mappings: AIMapping[];
}

export interface AuditPage {
  items: AuditItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardStats {
  total_audits: number;
  average_score: number | null;
  pending_ai_reviews: number;
  by_vendor: Record<string, number>;
  by_grade: Record<string, number>;
  failed_by_severity: Record<string, number>;
  score_trend: { id: number; created_at: string; filename: string; score: number | null }[];
  top_failing_rules: { rule_id: string; title: string; severity: Severity; count: number }[];
  recent: AuditItem[];
}

export interface FindingChange {
  rule_id: string;
  title: string;
  severity: Severity;
  base_status: FindingStatus | null;
  target_status: FindingStatus | null;
  change: "improved" | "regressed" | "unchanged";
}

export interface AuditComparison {
  base: AuditItem;
  target: AuditItem;
  score_delta: number | null;
  changes: FindingChange[];
}

export interface Rule {
  id: string;
  title: string;
  category: string;
  severity: Severity;
  description: string;
  vendors: string[] | null;
  remediation: Record<string, string>;
  references: Reference[];
}

export interface RuleCatalog {
  catalog_version: string;
  disclaimer: string;
  rules: Rule[];
}

export interface User {
  id: number;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface GenerateResult {
  created: number;
  skipped_over_limit: number;
  ai_used: boolean;
  ai_error: string | null;
  ai_configured: boolean;
}
