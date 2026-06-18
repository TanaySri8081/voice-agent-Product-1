import { Search, Play, FileText, Download } from "lucide-react";
import { useState, useMemo } from "react";
import DataTable from "../components/DataTable";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { callLogs } from "../data/mockData";

export default function CallLogs() {
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () =>
      callLogs.filter(
        (log) =>
          `${log.customer} ${log.agent} ${log.outcome}`
            .toLowerCase()
            .includes(query.toLowerCase())
      ),
    [query]
  );

  const toneFor = (outcome) => {
    if (["Converted", "Transferred"].includes(outcome)) return "success";
    if (["Follow-up", "Interested"].includes(outcome)) return "warning";
    if (outcome === "No Answer") return "neutral";
    return "danger";
  };

  const columns = [
    { key: "id", header: "Call ID" },
    { key: "customer", header: "Customer" },
    { key: "agent", header: "Agent" },
    { key: "duration", header: "Duration" },
    {
      key: "outcome",
      header: "Outcome",
      render: (row) => <Badge tone={toneFor(row.outcome)}>{row.outcome}</Badge>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => (
        <div className="flex gap-2">
          {row.recording === "Ready" && (
            <Button variant="secondary" size="sm" title="Listen to recording">
              <Play className="h-3.5 w-3.5" />
            </Button>
          )}
          {row.transcript !== "None" && (
            <Button variant="secondary" size="sm" title="View transcript">
              <FileText className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button variant="secondary" size="sm" title="Download metadata">
            <Download className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Call Logs</h1>
        <p className="mt-2 text-sm text-gray-500">History of all calls handled by your outbound AI agents.</p>
      </div>

      <div className="panel flex flex-col gap-3 rounded-3xl p-4 md:flex-row">
        <label className="flex flex-1 items-center gap-3 rounded-2xl border border-gray-200 px-3 py-2">
          <Search className="h-4 w-4 text-gray-400" />
          <input
            className="w-full border-0 outline-none"
            placeholder="Search logs by customer, agent, or outcome..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>

      <DataTable columns={columns} rows={filtered} emptyTitle="No call logs match your query" />
    </div>
  );
}
