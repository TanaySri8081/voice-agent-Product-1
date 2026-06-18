import { Search, Plus, PhoneCall, Globe, ShieldCheck } from "lucide-react";
import { useState, useMemo } from "react";
import DataTable from "../components/DataTable";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { phoneNumbers } from "../data/mockData";

export default function PhoneNumbers() {
  const [query, setQuery] = useState("");
  const filtered = useMemo(
    () =>
      phoneNumbers.filter(
        (num) =>
          `${num.number} ${num.country} ${num.provider}`
            .toLowerCase()
            .includes(query.toLowerCase())
      ),
    [query]
  );

  const columns = [
    { key: "number", header: "Phone Number" },
    { key: "country", header: "Country" },
    { key: "provider", header: "Carrier/Provider" },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <Badge tone={row.status === "Active" ? "success" : "neutral"}>
          {row.status}
        </Badge>
      ),
    },
    { key: "type", header: "Type" },
    {
      key: "actions",
      header: "Actions",
      render: (row) => (
        <Button variant="secondary" size="sm">
          {row.status === "Active" ? "Configure" : "Claim Number"}
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Phone Numbers</h1>
          <p className="mt-2 text-sm text-gray-500">
            Provision and configure Twilio or custom SIP numbers for outbound caller IDs.
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4" /> Provision Number
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <article className="panel rounded-3xl p-5 flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">
            <Globe className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-950">Global Reach</h2>
            <p className="mt-1 text-sm text-gray-500">
              Rent local, toll-free, or mobile phone numbers in over 100 countries.
            </p>
          </div>
        </article>

        <article className="panel rounded-3xl p-5 flex items-start gap-4">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-amber-50 text-amber-700">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-950">SHAKEN/STIR & CNAM</h2>
            <p className="mt-1 text-sm text-gray-500">
              Verify your numbers to prevent them from showing up as "Spam Risk" on customer screens.
            </p>
          </div>
        </article>
      </div>

      <div className="panel flex flex-col gap-3 rounded-3xl p-4 md:flex-row">
        <label className="flex flex-1 items-center gap-3 rounded-2xl border border-gray-200 px-3 py-2">
          <Search className="h-4 w-4 text-gray-400" />
          <input
            className="w-full border-0 outline-none"
            placeholder="Search phone numbers by carrier, number, or country..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>

      <DataTable columns={columns} rows={filtered} emptyTitle="No numbers match your query" />
    </div>
  );
}
