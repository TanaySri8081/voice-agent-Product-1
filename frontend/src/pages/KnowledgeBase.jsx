import { Search, Upload, BookOpen, Trash2, CheckCircle2, RotateCw } from "lucide-react";
import { useState, useMemo } from "react";
import DataTable from "../components/DataTable";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { knowledgeDocs } from "../data/mockData";

export default function KnowledgeBase() {
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () =>
      knowledgeDocs.filter(
        (doc) =>
          `${doc.name} ${doc.type}`.toLowerCase().includes(query.toLowerCase())
      ),
    [query]
  );

  const columns = [
    { key: "name", header: "Document Name" },
    { key: "type", header: "Type" },
    {
      key: "status",
      header: "Status",
      render: (row) => {
        const tone =
          row.status === "Synced"
            ? "success"
            : row.status === "Training"
            ? "warning"
            : "danger";
        return <Badge tone={tone}>{row.status}</Badge>;
      },
    },
    {
      key: "actions",
      header: "Actions",
      render: () => (
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" title="Re-sync">
            <RotateCw className="h-3.5 w-3.5" />
          </Button>
          <Button variant="danger" size="sm" title="Delete">
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Knowledge Base</h1>
          <p className="mt-2 text-sm text-gray-500">
            Upload scripts, guidelines, and FAQs to educate your AI agents.
          </p>
        </div>
        <Button>
          <Upload className="h-4 w-4" /> Upload Document
        </Button>
      </div>

      <div className="panel flex flex-col gap-3 rounded-3xl p-4 md:flex-row">
        <label className="flex flex-1 items-center gap-3 rounded-2xl border border-gray-200 px-3 py-2">
          <Search className="h-4 w-4 text-gray-400" />
          <input
            className="w-full border-0 outline-none"
            placeholder="Search knowledge documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>

      <DataTable columns={columns} rows={filtered} emptyTitle="No documents found" />
    </div>
  );
}
