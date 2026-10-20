import { useState } from "react";
import { listMappings } from "../api/client";
import MappingCard from "../components/MappingCard";
import { Empty, ErrorNote, PageHeader, Spinner, useAsync } from "../components/ui";
import { cn } from "../lib/ui";

const TABS = ["pending", "approved", "rejected"] as const;

export default function AIReview() {
  const [status, setStatus] = useState<(typeof TABS)[number]>("pending");
  const { data, error, loading, reload } = useAsync(() => listMappings(status), [status]);
  return (
    <>
      <PageHeader title="AI review" subtitle="Suggested meanings for commands the parser did not recognize. A person must approve each one. Suggestions never change findings, scores or grades." />
      <div className="mb-4 flex gap-2">
        {TABS.map((t) => (
          <button key={t} onClick={() => setStatus(t)} aria-pressed={status === t}
            className={cn("rounded-full border px-3 py-1 text-sm capitalize", status === t ? "border-ink bg-ink text-white" : "border-line bg-paper text-ink hover:bg-mist")}>{t}</button>
        ))}
      </div>
      <ErrorNote error={error} />
      {loading && !data ? <Spinner /> : data && data.length === 0 ? <Empty>Nothing {status}. Open an audit’s “Unrecognized commands” tab to generate suggestions.</Empty> : (
        <div className="space-y-3">{data?.map((m) => <MappingCard key={m.id} m={m} onChanged={reload} showAudit />)}</div>
      )}
    </>
  );
}
