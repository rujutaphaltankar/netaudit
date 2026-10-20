import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, createAudit, getVendors } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, Card, ErrorNote, PageHeader, fieldCls } from "../components/ui";
import { formatBytes } from "../lib/format";
import { cn } from "../lib/ui";
import type { VendorInfo } from "../types";

const MAX_BYTES = 2 * 1024 * 1024; // mirrors MAX_UPLOAD_BYTES; the server is the authority
const ACCEPT = ".txt,.cfg,.conf,.config,.log,.set";

export default function NewAudit() {
  const { isAdmin } = useAuth();
  const navigate = useNavigate();
  const [vendors, setVendors] = useState<VendorInfo[]>([]);
  const [vendor, setVendor] = useState("auto");
  const [file, setFile] = useState<File | null>(null);
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getVendors().then(setVendors).catch(() => setVendors([]));
  }, []);

  if (!isAdmin) {
    return (
      <>
        <PageHeader title="New audit" />
        <Card><p className="text-sm">Your account is read-only. Ask an administrator to upload configurations; you can view all results under History.</p></Card>
      </>
    );
  }

  function pick(f: File | null) {
    setError(null);
    if (f && f.size === 0) return setError(new ApiError("empty_file", "The selected file is empty.", 400)), setFile(null);
    if (f && f.size > MAX_BYTES) return setError(new ApiError("file_too_large", `File is ${formatBytes(f.size)}; the limit is ${formatBytes(MAX_BYTES)}.`, 413)), setFile(null);
    setFile(f);
  }

  async function submit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const audit = await createAudit(file, vendor, force);
      navigate(`/audits/${audit.id}`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const mismatch = error instanceof ApiError && error.code === "vendor_mismatch";

  return (
    <>
      <PageHeader title="New audit" subtitle="Upload a device configuration. It is validated, parsed and checked against every rule; secrets are redacted and the raw file is never stored." />
      <Card className="max-w-3xl">
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0] ?? null); }}
          className={cn("rounded-lg border-2 border-dashed p-8 text-center transition-colors", drag ? "border-signal bg-signal-wash" : "border-line")}
        >
          <p className="text-sm text-ink">{file ? <><b>{file.name}</b> · {formatBytes(file.size)}</> : "Drop a configuration file here"}</p>
          <p className="mt-1 text-xs text-muted">Allowed: {ACCEPT} · max {formatBytes(MAX_BYTES)}</p>
          <Button className="mt-3" onClick={() => input.current?.click()}>Choose file</Button>
          <input ref={input} type="file" accept={ACCEPT} className="sr-only" aria-label="Configuration file" onChange={(e) => pick(e.target.files?.[0] ?? null)} />
        </div>

        <label className="mt-5 block text-sm font-medium text-ink">
          Vendor
          <select className={`${fieldCls} mt-1 max-w-xs`} value={vendor} onChange={(e) => { setVendor(e.target.value); setForce(false); }}>
            <option value="auto">Auto-detect</option>
            {vendors.map((v) => <option key={v.id} value={v.id} disabled={!v.supported}>{v.display_name}{v.supported ? "" : " (not supported yet)"}</option>)}
          </select>
        </label>

        {mismatch && (
          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} /> Parse as the selected vendor anyway
          </label>
        )}
        <div className="mt-4"><ErrorNote error={error} /></div>
        <Button variant="primary" className="mt-5" disabled={!file || busy} onClick={submit}>{busy ? "Auditing…" : "Run audit"}</Button>
      </Card>
    </>
  );
}
