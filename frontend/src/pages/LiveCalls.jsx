import { useEffect, useState, useCallback } from "react";
import { RefreshCw, Radio } from "lucide-react";
import api from "../lib/api";
import { Button } from "../components/ui/Button";
import EmptyState from "../components/EmptyState";

export default function LiveCalls() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/stats/live");
      setCalls(res.data?.success ? res.data.data || [] : []);
    } catch {
      setCalls([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Live Calls</h1>
          <p className="mt-2 text-sm text-gray-500">Calls your AI receptionist is handling right now.</p>
        </div>
        <Button variant="secondary" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4" /> {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {calls.length === 0 ? (
        <EmptyState title={loading ? "Checking for live calls…" : "No live calls right now"} />
      ) : (
        <section className="grid gap-5 xl:grid-cols-3">
          {calls.map((call) => (
            <article key={call.id} className="panel rounded-3xl p-5">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-950">{call.caller}</h2>
                  <p className="text-sm text-gray-500">{call.phone || "—"}</p>
                </div>
                <div className="flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                  <Radio className="h-3 w-3" /> Live
                </div>
              </div>
              <div className="mt-4 space-y-1 text-sm text-gray-500">
                <p>Direction: <span className="capitalize text-gray-900">{call.direction}</span></p>
                <p>Exchanges: <span className="text-gray-900">{call.turns}</span></p>
                <p>Started: <span className="text-gray-900">{call.startedAt ? new Date(call.startedAt).toLocaleTimeString() : "—"}</span></p>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
