import { BarChart, Bar, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Clock3, PhoneCall, Timer, Trophy, WalletCards } from "lucide-react";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import StatCard from "../components/StatCard";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { callOutcomes, dailyCalls, recentActivity, revenueAnalytics } from "../data/mockData";

const COLORS = ["#111827", "#6b7280", "#d1d5db", "#f59e0b"];

export default function Dashboard() {
  const columns = [
    { key: "callerName", header: "Caller Name" },
    { key: "phone", header: "Phone Number" },
    { key: "agent", header: "Agent Used" },
    { key: "duration", header: "Duration" },
    { key: "status", header: "Status", render: (row) => <Badge tone={toneFor(row.status)}>{row.status}</Badge> },
    { key: "date", header: "Date" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">Outbound command center</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-gray-950">Dashboard</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-500">
            Monitor call volume, answer rates, conversions, agent activity, and campaign performance in real time.
          </p>
        </div>
        <Button>Launch campaign</Button>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard title="Total Calls" value="18,420" change="+12.4%" icon={PhoneCall} />
        <StatCard title="Successful Calls" value="12,894" change="+8.7%" icon={Trophy} tone="light" />
        <StatCard title="Avg. Duration" value="3m 42s" change="-4.1%" icon={Timer} tone="light" />
        <StatCard title="Conversion Rate" value="24.8%" change="+3.6%" icon={WalletCards} tone="light" />
        <StatCard title="AI Minutes Used" value="64.2k" change="+16.2%" icon={Clock3} tone="light" />
      </section>

      <section className="grid gap-6 xl:grid-cols-3">
        <ChartCard title="Daily outbound calls" description="Calls, answered calls, and conversions this week">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dailyCalls}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="day" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} />
              <Tooltip />
              <Line type="monotone" dataKey="calls" stroke="#111827" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="answered" stroke="#6b7280" strokeWidth={3} dot={false} />
              <Line type="monotone" dataKey="conversions" stroke="#f59e0b" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Call outcomes" description="Outcome distribution across all agents">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={callOutcomes} dataKey="value" nameKey="name" innerRadius={62} outerRadius={98} paddingAngle={4}>
                {callOutcomes.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Revenue analytics" description="Attributed revenue by campaign">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={revenueAnalytics}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="campaign" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} />
              <Tooltip />
              <Bar dataKey="revenue" fill="#111827" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-950">Recent activity</h2>
          <Button variant="secondary">Export CSV</Button>
        </div>
        <DataTable columns={columns} rows={recentActivity} />
      </section>
    </div>
  );
}

function toneFor(status) {
  if (["Converted", "Transferred"].includes(status)) return "success";
  if (["Follow-up", "Interested"].includes(status)) return "warning";
  if (status === "No Answer") return "neutral";
  return "danger";
}
