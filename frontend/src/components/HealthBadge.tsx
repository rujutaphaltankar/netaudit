import { useEffect, useState } from "react";
import { getHealth } from "../api/client";
import type { Health } from "../types";

export default function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setFailed(true));
  }, []);

  if (failed) {
    return <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">Backend unreachable</span>;
  }
  if (!health) {
    return <span className="rounded-full bg-slate-200 px-3 py-1 text-xs text-slate-600">Checking backend…</span>;
  }
  const db = { ok: "database connected", not_configured: "database not configured", unavailable: "database unavailable" }[health.database];
  const tone = health.database === "unavailable" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800";
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium ${tone}`} title={`API v${health.version} · AI: ${health.ai_assistance}`}>
      Backend online · {db}
    </span>
  );
}
