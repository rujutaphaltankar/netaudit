import { useState } from "react";
import HealthBadge from "./components/HealthBadge";
import ParseResultView from "./components/ParseResultView";
import UploadForm from "./components/UploadForm";
import type { ConfigParseResponse } from "./types";

export default function App() {
  const [result, setResult] = useState<ConfigParseResponse | null>(null);

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Network Security Compliance Auditor</h1>
            <p className="text-sm text-slate-500">Multi-vendor configuration analysis · Cisco IOS &amp; Juniper Junos</p>
          </div>
          <HealthBadge />
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-6">
        <UploadForm onResult={setResult} />
        {result ? (
          <ParseResultView data={result} />
        ) : (
          <p className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
            No configuration analyzed yet. Upload a file to see extracted settings, evidence and unknowns.
          </p>
        )}
      </main>
    </div>
  );
}
