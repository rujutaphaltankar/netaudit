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
    const t = setTimeout(() => { setQ(search); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data, error, loading } = useAsync(() => listAudits({ page, pageSize: PAGE_SIZE, vendor: vendor || undefined, q: q || undefined }), [page, vendor, q]);
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
      <PageHeader title="Audit history" subtitle="Every audit is stored with its findings. Select two audits to see what improved or regressed." actions={<Link to="/audits/new"><Button variant="primary">New audit</Button></Link>} />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input aria-label="Search" className={cn(inputCls, "w-64")} placeholder="Search file or hostname" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select aria-label="Vendor" className={cn(inputCls, "w-auto")} value={vendor} onChange={(e) => { setVendor(e.target.value); setPage(1); }}>
          <option value="">All vendors</option><option value="cisco_ios">Cisco IOS</option><option value="juniper_junos">Juniper Junos</option>
        </select>
        <Button disabled={picked.length !== 2} onClick={compare}>Compare selected ({picked.length}/2)</Button>
      </div>
      <ErrorNote error={error} />
      {loading && !data ? <Spinner /> : data && data.items.length === 0 ? <Empty>No audits found.</Empty> : data && (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-b border-line text-xs text-muted"><tr>
              <th className="w-10 p-3"><span className="sr-only">Select</span></th><th className="p-3">Device / file</th><th className="p-3">Vendor</th>
              <th className="p-3">Score</th><th className="p-3">Failed</th><th className="p-3">Date</th>
            </tr></thead>
            <tbody className="divide-y divide-line">
              {data.items.map((a) => (
                <tr key={a.id} className="hover:bg-mist/60">
                  <td className="p-3"><input type="checkbox" aria-label={`Select audit ${a.id}`} checked={picked.includes(a.id)} onChange={() => toggle(a.id)} /></td>
                  <td className="p-3"><Link to={`/audits/${a.id}`} className="font-medium text-ink hover:text-signal">{a.hostname ?? a.filename}</Link><div className="text-xs text-muted">#{a.id} · {a.filename}</div></td>
                  <td className="p-3">{vendorLabel(a.vendor)}</td>
                  <td className="p-3"><span className="mr-2 inline-grid size-6 place-items-center rounded text-xs font-semibold text-white" style={{ background: gradeHex(a.grade) }}>{a.grade}</span>{formatScore(a.score)}</td>
                  <td className="p-3">{a.failed}</td>
                  <td className="p-3 text-muted">{formatDate(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {data && data.total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-muted">{data.total} audits · page {page} of {pages}</span>
          <div className="flex gap-2"><Button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><Button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button></div>
        </div>
      )}
    </>
  );
}
