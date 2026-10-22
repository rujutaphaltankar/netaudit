import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listAudits } from "../api/client";
import { Button, Card, Empty, ErrorNote, PageHeader, Spinner, inputCls, useAsync } from "../components/ui";
import { cn, formatDate, formatScore, gradeHex, vendorLabel } from "../lib/ui";

const PAGE_SIZE = 10;

export default function History() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [vendor, setVendor] = useState("");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<number[]>([]);

  useEffect(() => {
    const t = setTimeout(() => {
      setQ(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, error, loading } = useAsync(
    () => listAudits({ page, pageSize: PAGE_SIZE, vendor: vendor || undefined, q: q || undefined }),
    [page, vendor, q]
  );
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  function toggle(id: number) {
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length >= 2 ? [p[1], id] : [...p, id]));
  }

  function compare() {
    const [a, b] = [...picked].sort((x, y) => x - y); // older audit is the baseline
    navigate(`/audits/compare?base=${a}&target=${b}`);
  }

  return (
    <>
      <PageHeader
        title="Audit history"
        subtitle="Every audit is permanently archived with its full findings and parsed configuration. Select any two audits to analyze compliance drift."
        actions={
          <Link to="/audits/new">
            <Button variant="primary">+ New audit</Button>
          </Link>
        }
      />
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <input
              aria-label="Search"
              className={cn(inputCls, "w-64 pr-7 text-xs")}
              placeholder="Search file, hostname, or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted hover:text-ink"
                title="Clear search"
              >
                ✕
              </button>
            )}
          </div>
          <select
            aria-label="Vendor"
            className={cn(inputCls, "w-auto text-xs")}
            value={vendor}
            onChange={(e) => {
              setVendor(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All vendors</option>
            <option value="cisco_ios">Cisco IOS</option>
            <option value="juniper_junos">Juniper Junos</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          {picked.length > 0 && (
            <button
              type="button"
              onClick={() => setPicked([])}
              className="text-xs text-muted hover:text-ink underline"
            >
              Clear selection ({picked.length})
            </button>
          )}
          <Button
            variant={picked.length === 2 ? "primary" : "secondary"}
            disabled={picked.length !== 2}
            onClick={compare}
            className="text-xs"
          >
            Compare selected ({picked.length}/2)
          </Button>
        </div>
      </div>

      <ErrorNote error={error} />
      {loading && !data ? (
        <Spinner />
      ) : data && data.items.length === 0 ? (
        <Empty>No audits found matching your query.</Empty>
      ) : (
        data && (
          <Card className="overflow-x-auto p-0 shadow-xs">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <thead className="border-b border-line bg-mist/40 text-xs font-semibold text-muted uppercase tracking-wider">
                <tr>
                  <th className="w-10 p-3.5">
                    <span className="sr-only">Select</span>
                  </th>
                  <th className="p-3.5">Device / file</th>
                  <th className="p-3.5">Vendor</th>
                  <th className="p-3.5">Score</th>
                  <th className="p-3.5">Failed Checks</th>
                  <th className="p-3.5">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.items.map((a) => {
                  const isSelected = picked.includes(a.id);
                  return (
                    <tr
                      key={a.id}
                      className={cn(
                        "transition-colors",
                        isSelected ? "bg-signal-wash/40 font-medium" : "hover:bg-mist/50"
                      )}
                    >
                      <td className="p-3.5">
                        <input
                          type="checkbox"
                          aria-label={`Select audit ${a.id}`}
                          checked={isSelected}
                          onChange={() => toggle(a.id)}
                          className="size-4 rounded accent-signal cursor-pointer"
                        />
                      </td>
                      <td className="p-3.5">
                        <Link to={`/audits/${a.id}`} className="font-semibold text-ink hover:text-signal transition-colors">
                          {a.hostname ?? a.filename}
                        </Link>
                        <div className="text-xs text-muted">
                          #{a.id} · {a.filename}
                        </div>
                      </td>
                      <td className="p-3.5 text-xs text-body">{vendorLabel(a.vendor)}</td>
                      <td className="p-3.5">
                        <div className="flex items-center gap-2">
                          <span
                            className="grid size-6 place-items-center rounded text-xs font-bold text-white shadow-xs"
                            style={{ background: gradeHex(a.grade) }}
                          >
                            {a.grade}
                          </span>
                          <span className="font-mono font-bold text-ink">{formatScore(a.score)}</span>
                        </div>
                      </td>
                      <td className="p-3.5">
                        <span
                          className={cn(
                            "rounded px-2 py-0.5 text-xs font-semibold",
                            a.failed > 0 ? "bg-crit-wash text-crit" : "bg-pass-wash text-pass"
                          )}
                        >
                          {a.failed} failed
                        </span>
                      </td>
                      <td className="p-3.5 text-xs text-muted">{formatDate(a.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        )
      )}
      {data && data.total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-muted text-xs">
            {data.total} audits · page {page} of {pages}
          </span>
          <div className="flex gap-2">
            <Button disabled={page <= 1} onClick={() => setPage(page - 1)} className="text-xs py-1">
              Previous
            </Button>
            <Button disabled={page >= pages} onClick={() => setPage(page + 1)} className="text-xs py-1">
              Next
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
