import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import api from "../lib/api";
import DataTable from "../components/DataTable";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

const kindTone = (k) => ((k || "").toLowerCase() === "reminder" ? "warning" : "neutral");
const statusTone = (s) => ((s || "").toLowerCase() === "sent" ? "success" : "danger");

export default function Messages() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(() => {
    setRefreshing(true);
    api.get("/messages/whatsapp")
      .then((r) => setRows(r.data?.success ? r.data.data || [] : []))
      .catch(() => setRows([]))
      .finally(() => setRefreshing(false));
  }, []);

  useEffect(() => {
    api.get("/messages/whatsapp")
      .then((r) => setRows(r.data?.success ? r.data.data || [] : []))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  const columns = [
    { key: "created_at", header: "When", render: (r) => (r.created_at ? new Date(r.created_at).toLocaleString() : "—") },
    { key: "to_phone", header: "To", render: (r) => r.to_phone || "—" },
    { key: "kind", header: "Type", render: (r) => <Badge tone={kindTone(r.kind)}>{r.kind}</Badge> },
    { key: "body", header: "Message", render: (r) => r.body || "—" },
    { key: "status", header: "Status", render: (r) => <Badge tone={statusTone(r.status)}>{r.status}</Badge> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Messages</h1>
          <p className="mt-2 text-sm text-gray-500">WhatsApp confirmations and reminders sent to your customers.</p>
        </div>
        <Button variant="secondary" onClick={refresh} disabled={refreshing}>
          <RefreshCw className="h-4 w-4" /> {refreshing ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      <DataTable columns={columns} rows={rows} loading={loading} emptyTitle="No WhatsApp messages sent yet" />
    </div>
  );
}
