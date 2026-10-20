import { useEffect, useState } from "react";
import { getHealth } from "../api/client";
import type { Health } from "../types";

export default function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    getHealth().then(setHealth).catch(() => setFailed(true));
  }, []);

  const dot = failed || health?.database === "unavailable" ? "bg-[#e5484d]" : health ? "bg-[#3ecf8e]" : "bg-slate-500";
  const text = failed ? "Backend unreachable" : !health ? "Checking backend…" : `API v${health.version} · DB ${health.database}`;
  return (
    <div className="text-xs text-white/60" title={health ? `AI assistance: ${health.ai_assistance}` : undefined}>
      <span className={`mr-2 inline-block size-2 rounded-full ${dot}`} />
      {text}
      {health && <div className="mt-0.5 pl-4">AI: {health.ai_assistance === "enabled" ? "enabled" : "rule-based fallback"}</div>}
    </div>
  );
}
