"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  GitBranch,
  Loader2,
  PhoneIncoming,
  RefreshCw,
  Server,
  TriangleAlert,
} from "lucide-react";

type InboundStatus = {
  workerName: string;
  trunks: Array<{ id: string; name: string; numbers: string[] }>;
  rules: Array<{ id: string; name: string; trunkIds: string[]; agentNames: string[] }>;
  activeRooms: Array<{ name: string; participants: number }>;
  error?: string;
};

const emptyStatus: InboundStatus = {
  workerName: "inbound-caller",
  trunks: [],
  rules: [],
  activeRooms: [],
};

export default function InboundConsole() {
  const [status, setStatus] = useState<InboundStatus>(emptyStatus);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/inbound/status", { cache: "no-store" });
      const data = await response.json();
      setStatus(response.ok ? data : { ...emptyStatus, error: data.error });
    } catch (error) {
      setStatus({
        ...emptyStatus,
        error: error instanceof Error ? error.message : "Unable to load inbound status.",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = window.setInterval(refresh, 10000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const routedToWorker = status.rules.some((rule) =>
    rule.agentNames.includes(status.workerName),
  );

  return (
    <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <div className="overflow-hidden rounded-lg border border-white/10 bg-zinc-950/80 shadow-2xl shadow-black/30">
        <div className="flex items-center justify-between gap-4 border-b border-white/10 px-6 py-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-cyan-300">
              Live operations
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-white">Inbound Calls</h2>
          </div>
          <button
            type="button"
            onClick={refresh}
            disabled={loading}
            title="Refresh status"
            className="grid h-10 w-10 place-items-center rounded-md border border-white/10 bg-white/[0.04] text-zinc-300 transition hover:bg-white/[0.08] disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </button>
        </div>

        <div className="p-6">
          {status.error ? (
            <div className="flex items-start gap-3 rounded-md border border-red-400/20 bg-red-400/10 p-4 text-sm text-red-100">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{status.error}</span>
            </div>
          ) : status.activeRooms.length === 0 ? (
            <div className="grid min-h-52 place-items-center rounded-md border border-dashed border-white/10 bg-white/[0.02] p-8 text-center">
              <div>
                <PhoneIncoming className="mx-auto h-8 w-8 text-zinc-600" />
                <p className="mt-4 font-medium text-zinc-200">Waiting for inbound calls</p>
                <p className="mt-1 text-sm text-zinc-500">Active calls will appear here automatically.</p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {status.activeRooms.map((room) => (
                <div key={room.name} className="flex items-center justify-between rounded-md border border-emerald-400/20 bg-emerald-400/10 p-4">
                  <div className="flex items-center gap-3">
                    <Activity className="h-4 w-4 text-emerald-300" />
                    <div>
                      <p className="font-medium text-white">{room.name}</p>
                      <p className="text-xs text-emerald-200/70">{room.participants} participants</p>
                    </div>
                  </div>
                  <span className="text-xs font-medium text-emerald-200">Live</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-white/10 bg-zinc-950/80 shadow-2xl shadow-black/30">
        <div className="border-b border-white/10 px-6 py-5">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-300">
            Infrastructure
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-white">Inbound Readiness</h2>
        </div>

        <div className="space-y-3 p-6">
          <StatusRow
            icon={Server}
            label="Inbound SIP trunk"
            detail={status.trunks[0]?.numbers.join(", ") || "Not configured"}
            ready={status.trunks.length > 0}
          />
          <StatusRow
            icon={GitBranch}
            label="Dispatch routing"
            detail={routedToWorker ? `Routes to ${status.workerName}` : "No inbound agent route"}
            ready={routedToWorker}
          />
          <StatusRow
            icon={PhoneIncoming}
            label="Active calls"
            detail={`${status.activeRooms.length} connected`}
            ready={status.activeRooms.length > 0}
            neutral
          />
        </div>
      </div>
    </section>
  );
}

function StatusRow({
  icon: Icon,
  label,
  detail,
  ready,
  neutral = false,
}: {
  icon: typeof Server;
  label: string;
  detail: string;
  ready: boolean;
  neutral?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-white/10 bg-white/[0.03] p-4">
      <div className="flex min-w-0 items-center gap-3">
        <Icon className="h-4 w-4 shrink-0 text-zinc-500" />
        <div className="min-w-0">
          <p className="text-sm font-medium text-zinc-200">{label}</p>
          <p className="truncate text-xs text-zinc-500">{detail}</p>
        </div>
      </div>
      {neutral ? (
        <span className="rounded-md border border-white/10 px-2 py-1 text-xs text-zinc-400">Monitor</span>
      ) : ready ? (
        <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-300" />
      ) : (
        <TriangleAlert className="h-4 w-4 shrink-0 text-amber-300" />
      )}
    </div>
  );
}
