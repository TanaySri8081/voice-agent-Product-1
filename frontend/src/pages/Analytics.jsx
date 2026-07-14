import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Clock, Phone, Timer } from "lucide-react";
import api from "../lib/api";
import ChartCard from "../components/ChartCard";
import StatCard from "../components/StatCard";

const fmtDuration = (s) => `${Math.floor((s || 0) / 60)}m ${(s || 0) % 60}s`;
const dayLabel = (iso) => {
  try {
    return new Date(iso).toLocaleDateString(undefined, { weekday: "short" });
  } catch {
    return iso;
  }
};

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/stats/overview")
      .then((res) => { if (res.data?.success) setData(res.data.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const calls = data?.calls || {};
  const daily = (data?.daily || []).map((d) => ({ ...d, label: dayLabel(d.date) }));
  const outcomes = data?.outcomes || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Analytics</h1>
        <p className="mt-2 text-sm text-gray-500">Call performance for your clinic.</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Calls (last 7 days)" value={loading ? "…" : (calls.last7Days ?? 0)} icon={Phone} tone="light" />
        <StatCard title="Total Minutes" value={loading ? "…" : (calls.totalMinutes ?? 0)} icon={Clock} tone="light" />
        <StatCard title="Avg Duration" value={loading ? "…" : fmtDuration(calls.avgDurationSec)} icon={Timer} tone="light" />
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <ChartCard title="Inbound call volume" description="Calls received over the last 7 days">
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

        <ChartCard title="Call outcomes" description="Calls grouped by status">
          {outcomes.length === 0 ? (
            <div className="grid h-full place-items-center text-sm text-gray-400">No call data yet</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={outcomes}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="status" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#111827" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </section>
    </div>
  );
}
