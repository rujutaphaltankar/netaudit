import { useMemo, useState } from "react";
import { getRules } from "../api/client";
import { Card, Chip, ErrorNote, PageHeader, SeverityBadge, Spinner, fieldCls, useAsync } from "../components/ui";
import { vendorLabel } from "../lib/ui";

export default function Rules() {
  const { data, error, loading } = useAsync(getRules, []);
  const [q, setQ] = useState("");
  const grouped = useMemo(() => {
    const m = new Map<string, NonNullable<typeof data>["rules"]>();
    for (const r of data?.rules ?? []) {
      if (q && !`${r.id} ${r.title} ${r.description}`.toLowerCase().includes(q.toLowerCase())) continue;
      m.set(r.category, [...(m.get(r.category) ?? []), r]);
    }
    return [...m.entries()];
  }, [data, q]);

  if (loading) return <Spinner />;
  if (error || !data) return <ErrorNote error={error} />;
  return (
    <>
      <PageHeader title="Rules library" subtitle={`${data.rules.length} deterministic checks · catalog v${data.catalog_version}. Each rule explains why it matters, how to fix it per vendor, and the controls it relates to.`} />
      <p className="mb-4 rounded-md border border-med/30 bg-med-wash p-3 text-sm text-med">{data.disclaimer}</p>
      <input aria-label="Search rules" className={`${fieldCls} mb-5 max-w-sm`} placeholder="Search rules" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="space-y-6">
        {grouped.map(([cat, rules]) => (
          <section key={cat}>
            <h2 className="mb-2 text-base font-semibold">{cat}</h2>
            <div className="space-y-2.5">
              {rules.map((r) => (
                <details key={r.id} className="group rounded-lg border border-line bg-paper">
                  <summary className="flex cursor-pointer flex-wrap items-center gap-2 p-3.5 hover:bg-mist/60">
                    <SeverityBadge severity={r.severity} /><span className="font-mono text-xs text-muted">{r.id}</span>
                    <span className="min-w-0 flex-1 font-medium text-ink">{r.title}</span>
                    <span className="text-muted transition-transform group-open:rotate-90" aria-hidden>›</span>
                  </summary>
                  <div className="space-y-3 border-t border-line p-4 text-sm">
                    <p>{r.description}</p>
                    <p className="text-xs text-muted">Applies to: {r.vendors ? r.vendors.map(vendorLabel).join(", ") : "all supported vendors"}</p>
                    {Object.entries(r.remediation).map(([k, v]) => (
                      <div key={k}><div className="mb-1 text-xs font-medium text-muted">{k === "generic" ? "General guidance" : vendorLabel(k)}</div>
                        <pre className="overflow-x-auto rounded-md bg-ink p-3 font-mono text-xs text-[#cfe9eb]">{v}</pre></div>
                    ))}
                    <div className="flex flex-wrap gap-1.5">{r.references.map((x) => <span key={x.framework + x.control} title={x.title}><Chip tone="bg-signal-wash text-signal-dark">{x.framework} · {x.control}</Chip></span>)}</div>
                  </div>
                </details>
              ))}
            </div>
          </section>
        ))}
        {grouped.length === 0 && <Card>No rules match “{q}”.</Card>}
      </div>
    </>
  );
}
