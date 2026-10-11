import { useEffect, useRef, useState } from "react";
import { ApiError, getVendors, parseConfig } from "../api/client";
import { formatBytes } from "../lib/format";
import type { ConfigParseResponse, VendorInfo } from "../types";

// Mirrors the backend default (MAX_UPLOAD_BYTES). The server remains the authority.
const MAX_BYTES = 2 * 1024 * 1024;
const ACCEPT = ".txt,.cfg,.conf,.config,.log,.set";

interface Props {
  onResult: (r: ConfigParseResponse) => void;
}

export default function UploadForm({ onResult }: Props) {
  const [vendors, setVendors] = useState<VendorInfo[]>([]);
  const [vendor, setVendor] = useState("auto");
  const [file, setFile] = useState<File | null>(null);
  const [force, setForce] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getVendors().then(setVendors).catch(() => setVendors([]));
  }, []);

  function pick(f: File | null) {
    setError(null);
    if (f && f.size > MAX_BYTES) {
      setFile(null);
      setError(`File is ${formatBytes(f.size)}; the limit is ${formatBytes(MAX_BYTES)}.`);
      return;
    }
    if (f && f.size === 0) {
      setFile(null);
      setError("The selected file is empty.");
      return;
    }
    setFile(f);
  }

  async function submit() {
    if (!file) {
      setError("Choose a configuration file first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      onResult(await parseConfig(file, vendor, force));
    } catch (e) {
      setError(e instanceof ApiError ? e : "Unexpected error while uploading.");
    } finally {
      setLoading(false);
    }
  }

  const message = typeof error === "string" ? error : error?.message;
  const mismatch = typeof error !== "string" && error?.code === "vendor_mismatch";

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Upload a device configuration</h2>
      <p className="mt-1 text-sm text-slate-600">
        The file is validated, parsed and normalized in memory. Secrets are redacted from all evidence.
      </p>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="block text-sm font-medium">
          Configuration file
          <input
            ref={input}
            type="file"
            accept={ACCEPT}
            onChange={(e) => pick(e.target.files?.[0] ?? null)}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-indigo-50 file:px-3 file:py-1 file:text-indigo-700"
          />
          <span className="mt-1 block text-xs font-normal text-slate-500">
            {file ? `${file.name} · ${formatBytes(file.size)}` : `Allowed: ${ACCEPT} · max ${formatBytes(MAX_BYTES)}`}
          </span>
        </label>

        <label className="block text-sm font-medium">
          Vendor
          <select
            value={vendor}
            onChange={(e) => {
              setVendor(e.target.value);
              setForce(false);
            }}
            className="mt-1 block w-full rounded-md border border-slate-300 bg-white p-2 text-sm"
          >
            <option value="auto">Auto-detect</option>
            {vendors.map((v) => (
              <option key={v.id} value={v.id} disabled={!v.supported}>
                {v.display_name}
                {v.supported ? "" : " (not supported yet)"}
              </option>
            ))}
          </select>
        </label>
      </div>

      {mismatch && (
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
          Parse as the selected vendor anyway
        </label>
      )}

      {message && (
        <div role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {message}
          {typeof error !== "string" && error?.code && <span className="ml-2 font-mono text-xs text-red-500">[{error.code}]</span>}
        </div>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={loading || !file}
        className="mt-5 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Analyzing…" : "Analyze configuration"}
      </button>
    </section>
  );
}
