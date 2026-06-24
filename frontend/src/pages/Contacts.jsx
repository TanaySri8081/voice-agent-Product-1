import { Filter, Search, Upload } from "lucide-react";
import { useMemo, useState, useEffect } from "react";
import axios from "axios";
import DataTable from "../components/DataTable";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { contacts } from "../data/mockData";

export default function Contacts() {
  const [list, setList] = useState([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    axios.get("http://localhost:8002/api/patients")
      .then(res => {
        if (res.data && res.data.success && res.data.data.length > 0) {
          // Map backend patient schema keys to table expectations
          const formatted = res.data.data.map(p => ({
            id: p.id,
            name: p.name,
            phone: p.phone,
            email: p.email || "N/A",
            company: p.gender ? `${p.gender}, Age ${p.age || 'N/A'}` : "Patient",
            lastContacted: p.follow_up_notes || "Never",
            status: p.history && p.history.length > 0 ? "Qualified" : "Interested"
          }));
          setList(formatted);
        } else {
          setList(contacts);
        }
      })
      .catch(() => {
        setList(contacts);
      });
  }, []);

  const filtered = useMemo(
    () => list.filter((contact) => `${contact.name} ${contact.company} ${contact.email}`.toLowerCase().includes(query.toLowerCase())),
    [query, list],
  );

  const columns = [
    { key: "name", header: "Name" },
    { key: "phone", header: "Phone" },
    { key: "email", header: "Email" },
    { key: "company", header: "Demographics / Context" },
    { key: "lastContacted", header: "Follow-up / Notes" },
    { key: "status", header: "Status", render: (row) => <Badge tone={row.status === "Converted" || row.status === "Qualified" ? "success" : row.status === "No Answer" ? "neutral" : "warning"}>{row.status}</Badge> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Contacts</h1>
          <p className="mt-2 text-sm text-gray-500">Import, search, and segment contacts for outbound campaigns.</p>
        </div>
        <Button><Upload className="h-4 w-4" /> Import contacts</Button>
      </div>
      <div className="panel flex flex-col gap-3 rounded-3xl p-4 md:flex-row">
        <label className="flex flex-1 items-center gap-3 rounded-2xl border border-gray-200 px-3 py-2">
          <Search className="h-4 w-4 text-gray-400" />
          <input className="w-full border-0 outline-none" placeholder="Search contacts..." value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <Button variant="secondary"><Filter className="h-4 w-4" /> Filter</Button>
      </div>
      <DataTable columns={columns} rows={filtered} emptyTitle="No contacts match your filters" />
    </div>
  );
}
