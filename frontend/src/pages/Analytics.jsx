import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, LineChart, Line } from "recharts";
import { BarChart3, Users, Award, TrendingUp } from "lucide-react";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import StatCard from "../components/StatCard";
import { agentPerformance, dailyCalls, revenueAnalytics } from "../data/mockData";

export default function Analytics() {
  const columns = [
    { key: "agent", header: "Agent Name" },
    { key: "calls", header: "Total Calls" },
    { key: "conversions", header: "Conversions" },
    { key: "csat", header: "CSAT Score", render: (row) => `${row.csat}%` },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Analytics</h1>
        <p className="mt-2 text-sm text-gray-500">Analyze performance, conversion rates, and agent metrics.</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Total Calls (Week)" value="2,710" change="+8.3%" icon={Users} tone="light" />
        <StatCard title="Best Agent CSAT" value="96%" change="+2.1%" icon={Award} tone="light" />
        <StatCard title="Average CSAT" value="92.5%" change="+0.8%" icon={TrendingUp} tone="light" />
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <ChartCard title="Outbound Call Volume" description="Calls made daily this week">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={dailyCalls}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="day" tickLine={false} axisLine={false} />
              <YAxis tickLine={false} axisLine={false} />
              <Tooltip />
              <Line type="monotone" dataKey="calls" stroke="#111827" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Campaign Performance" description="Attributed revenue by campaign">
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
        <h2 className="text-lg font-semibold text-gray-950">AI Agent Performance</h2>
        <DataTable columns={columns} rows={agentPerformance} />
      </section>
    </div>
  );
}
