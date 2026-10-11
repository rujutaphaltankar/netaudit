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
