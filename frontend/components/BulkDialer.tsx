"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileText,
  Loader2,
  Megaphone,
  PhoneForwarded,
  Users,
} from "lucide-react";

const campaignTypes = [
  "Automated Call Campaign",
  "Appointment Reminder",
  "Lead Qualification",
  "Payment / Billing Reminder",
  "Customer Feedback",
  "Order / Delivery Update",
  "Survey / Research",
  "Follow-up Call",
  "Voice Broadcast",
];

export default function BulkDialer() {
  const [input, setInput] = useState("");
  const [campaignType, setCampaignType] = useState(campaignTypes[0]);
  const [prompt, setPrompt] = useState("");
  const [scheduleWindow, setScheduleWindow] = useState("Now");
  const [transferNumber, setTransferNumber] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [results, setResults] = useState<Array<{ phoneNumber: string; status: string; error?: string }>>([]);

  const parsedNumbers = useMemo(
    () => input.split(/[\n,]+/).map((s) => s.trim()).filter(Boolean),
    [input],
  );

  const handleBulkDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setResults([]);

    if (parsedNumbers.length === 0) {
      setStatus("error");
      return;
    }

    try {
      const res = await fetch("/api/queue", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          numbers: parsedNumbers,
          campaignType,
          prompt,
          scheduleWindow,
          transferNumber,
        }),
      });

      const data = await res.json();
      setResults(data.results || []);
      setStatus(res.ok ? "success" : "error");
    } catch {
      setStatus("error");
    }
  };

  return (
    <section className="rounded-lg border border-white/10 bg-[#11151a] shadow-2xl shadow-black/20">
      <div className="border-b border-white/10 px-6 py-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-300">
              Campaign queue
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-white">Bulk Outbound</h2>
          </div>
          <Megaphone className="h-5 w-5 text-emerald-300" />
        </div>
      </div>

      <form onSubmit={handleBulkDispatch} className="space-y-5 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Campaign Type" icon={ClipboardList}>
            <select
              value={campaignType}
              onChange={(e) => setCampaignType(e.target.value)}
              className="field-control"
            >
              {campaignTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Schedule Window" icon={Clock3}>
            <select
              value={scheduleWindow}
              onChange={(e) => setScheduleWindow(e.target.value)}
              className="field-control"
            >
              <option>Now</option>
              <option>Business hours</option>
              <option>Evening follow-up</option>
              <option>Manual review first</option>
            </select>
          </Field>
        </div>

        <Field label="Phone Numbers" icon={Users}>
          <textarea
            placeholder="+919876543210&#10;+919988776655&#10;+12125551234"
            required
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="field-control min-h-36 resize-none font-mono text-sm"
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Campaign Context" icon={FileText}>
            <textarea
              placeholder="Goal, offer, appointment details, invoice info, survey questions..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="field-control min-h-28 resize-none"
            />
          </Field>

          <Field label="Transfer Target" icon={PhoneForwarded}>
            <textarea
              placeholder="Human number and escalation rule, e.g. transfer interested leads to +91..."
              value={transferNumber}
              onChange={(e) => setTransferNumber(e.target.value)}
              className="field-control min-h-28 resize-none"
            />
          </Field>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <MiniStat label="Recipients" value={parsedNumbers.length.toString()} />
          <MiniStat label="Mode" value={scheduleWindow} />
          <MiniStat label="Facility" value={campaignType.split(" ")[0]} />
        </div>

        <button
          type="submit"
          disabled={status === "loading"}
          className="flex h-12 w-full items-center justify-center gap-2 rounded-md bg-emerald-500 px-5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {status === "loading" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Processing Queue
            </>
          ) : (
            <>
              <Megaphone className="h-4 w-4" /> Launch Campaign
            </>
          )}
        </button>

        {(status === "success" || status === "error") && (
          <div className="max-h-48 space-y-2 overflow-y-auto rounded-md border border-white/10 bg-black/20 p-3">
            {results.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-red-100">
                <AlertCircle className="h-4 w-4" />
                Add at least one phone number.
              </div>
            ) : (
              results.map((res, i) => (
                <div key={`${res.phoneNumber}-${i}`} className="flex items-center justify-between gap-3 rounded-md bg-white/[0.04] px-3 py-2 text-xs">
                  <span className="truncate font-mono text-zinc-300">{res.phoneNumber}</span>
                  {res.status === "dispatched" ? (
                    <span className="flex items-center gap-1 text-emerald-300">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Sent
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-300" title={res.error}>
                      <AlertCircle className="h-3.5 w-3.5" /> Failed
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        )}
      </form>
    </section>
  );
}

function Field({
  label,
  icon: Icon,
  children,
}: {
  label: string;
  icon: typeof Users;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="flex items-center gap-2 text-sm font-medium text-zinc-300">
        <Icon className="h-4 w-4 text-zinc-500" />
        {label}
      </span>
      {children}
    </label>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-white/10 bg-white/[0.03] p-3">
      <p className="truncate text-xs text-zinc-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
