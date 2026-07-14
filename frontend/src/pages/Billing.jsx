import { useEffect, useState } from "react";
import { CalendarCheck, Clock, Hash, PhoneCall, Users, UsersRound } from "lucide-react";
import api from "../lib/api";
import StatCard from "../components/StatCard";
import { Badge } from "../components/ui/Badge";

export default function Billing() {
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
  const plan = data?.plan || "free";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Plan & Usage</h1>
        <p className="mt-2 text-sm text-gray-500">Your current plan and usage so far.</p>
      </div>

      <article className="panel flex items-center justify-between rounded-3xl p-6">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Current plan</span>
          <p className="mt-2 text-2xl font-semibold capitalize text-gray-950">{loading ? "…" : plan}</p>
        </div>
        <Badge tone="dark">Active</Badge>
      </article>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard title="Total Calls" value={loading ? "…" : (totals.calls ?? 0)} icon={PhoneCall} tone="light" />
        <StatCard title="Total Minutes" value={loading ? "…" : (calls.totalMinutes ?? 0)} icon={Clock} tone="light" />
        <StatCard title="Appointments" value={loading ? "…" : (totals.appointments ?? 0)} icon={CalendarCheck} tone="light" />
        <StatCard title="Contacts" value={loading ? "…" : (totals.contacts ?? 0)} icon={Users} tone="light" />
        <StatCard title="Team Members" value={loading ? "…" : (totals.team ?? 0)} icon={UsersRound} tone="light" />
        <StatCard title="Numbers Connected" value={loading ? "…" : (totals.numbers ?? 0)} icon={Hash} tone="light" />
      </section>

      <p className="text-sm text-gray-400">
        Paid plans and invoicing aren't enabled yet. Usage above is shown for transparency.
      </p>
    </div>
  );
}
