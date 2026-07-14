import { useEffect, useState } from "react";
import { CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, CalendarCheck, PhoneCall, Timer, Users } from "lucide-react";
import api from "../lib/api";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import StatCard from "../components/StatCard";
import { Badge } from "../components/ui/Badge";

const COLORS = ["#111827", "#6b7280", "#d1d5db", "#f59e0b", "#10b981", "#ef4444"];

const fmtDuration = (s) => `${Math.floor((s || 0) / 60)}m ${(s || 0) % 60}s`;
const dayLabel = (iso) => {
  try {
    return new Date(iso).toLocaleDateString(undefined, { weekday: "short" });
  } catch {
    return iso;
  }
};
const toneFor = (status) => {
  const s = (status || "").toLowerCase();
  if (["completed", "active"].includes(s)) return "success";
  if (s === "transferred") return "warning";
  if (["failed", "no-answer"].includes(s)) return "danger";
  return "neutral";
};

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/stats/overview")
      .then((res) => { if (res.data?.success) setData(res.data.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totals = data?.totals || {};
  const calls = data?.calls || {};
  const daily = (data?.daily || []).map((d) => ({ ...d, label: dayLabel(d.date) }));
  const outcomes = data?.outcomes || [];
  const recent = data?.recent || [];

  const columns = [
    { key: "customer", header: "Caller" },
    { key: "phone", header: "Phone" },
    { key: "direction", header: "Direction", render: (row) => <span className="capitalize">{row.direction}</span> },
    { key: "duration", header: "Duration" },
    { key: "status", header: "Status", render: (row) => <Badge tone={toneFor(row.status)}>{row.status}</Badge> },
    { key: "date", header: "When", render: (row) => (row.date ? new Date(row.date).toLocaleString() : "—") },
  ];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium text-gray-500">Inbound reception center</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-gray-950">Dashboard</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-500">A live view of calls, appointments, and your AI receptionist's activity.</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard title="Total Calls" value={loading ? "…" : (totals.calls ?? 0)} icon={PhoneCall} />
        <StatCard title="Calls Today" value={loading ? "…" : (calls.today ?? 0)} icon={Activity} tone="light" />
        <StatCard title="Appointments" value={loading ? "…" : (totals.appointments ?? 0)} icon={CalendarCheck} tone="light" />
        <StatCard title="Contacts" value={loading ? "…" : (totals.contacts ?? 0)} icon={Users} tone="light" />
        <StatCard title="Avg Duration" value={loading ? "…" : fmtDuration(calls.avgDurationSec)} icon={Timer} tone="light" />
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <ChartCard title="Daily inbound calls" description="Calls received over the last 7 days">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={daily}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="label" tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#111827" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Call outcomes" description="Distribution by status">
          {outcomes.length === 0 ? (
            <div className="grid h-full place-items-center text-sm text-gray-400">No call data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={outcomes} dataKey="count" nameKey="status" innerRadius={62} outerRadius={98} paddingAngle={4}>
                  {outcomes.map((entry, index) => (
                    <Cell key={entry.status} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Calls this week" description="Total received in the last 7 days">
          <div className="grid h-full place-items-center">
            <div className="text-center">
              <p className="text-6xl font-semibold tracking-tight text-gray-950">{loading ? "…" : (calls.last7Days ?? 0)}</p>
              <p className="mt-2 text-sm text-gray-500">{calls.active ?? 0} active right now</p>
            </div>
          </div>
        </ChartCard>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-950">Recent calls</h2>
        <DataTable columns={columns} rows={recent} loading={loading} emptyTitle="No calls yet" />
      </section>
    </div>
  );
}
