"use client";

import { useMemo, useState } from "react";
import {
  CalendarClock,
  CheckCircle2,
  Headphones,
  Loader2,
  MessageSquare,
  Phone,
  Sparkles,
  TriangleAlert,
  UserCheck,
} from "lucide-react";

const campaignTemplates = [
  {
    id: "appointment_reminder",
    label: "Appointment Reminder",
    prompt: "Remind the customer about their upcoming appointment. Offer to confirm, reschedule, or cancel, then summarize their choice.",
  },
  {
    id: "lead_qualification",
    label: "Lead Qualification",
    prompt: "Qualify the lead by asking about need, timeline, budget, and interest level. Transfer to sales if they are ready to speak now.",
  },
  {
    id: "payment_reminder",
    label: "Payment Reminder",
    prompt: "Politely remind the customer about an outstanding payment. Capture whether they have paid, need help, or want a callback.",
  },
  {
    id: "feedback_collection",
    label: "Feedback Collection",
    prompt: "Ask for a rating and short feedback about the recent service. Capture issues and transfer urgent complaints to a human agent.",
  },
  {
    id: "delivery_update",
    label: "Order / Delivery Update",
    prompt: "Notify the customer about their order or delivery status. Confirm if the timing works and capture any delivery instructions.",
  },
];

export default function CallDispatcher() {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [campaignType, setCampaignType] = useState(campaignTemplates[0].id);
  const [prompt, setPrompt] = useState(campaignTemplates[0].prompt);
  const [transferNumber, setTransferNumber] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const selectedTemplate = useMemo(
    () => campaignTemplates.find((template) => template.id === campaignType),
    [campaignType],
  );

  const handleTemplateChange = (value: string) => {
    const template = campaignTemplates.find((item) => item.id === value);
    setCampaignType(value);
    if (template) {
      setPrompt(template.prompt);
    }
  };

  const handleDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setMessage("");

    const form = e.target as HTMLFormElement;
    const modelProvider = (form.elements.namedItem("modelProvider") as HTMLSelectElement).value;
    const voice = (form.elements.namedItem("voice") as HTMLSelectElement).value;

    try {
      const res = await fetch("/api/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phoneNumber,
          customerName,
          campaignType,
          prompt,
          transferNumber,
          modelProvider,
          voice,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setStatus("success");
        setMessage(`Outbound call dispatched to ${phoneNumber}`);
      } else {
        setStatus("error");
        setMessage(data.error || "Failed to dispatch call");
      }
    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Network error");
    }
  };

  return (
    <section className="rounded-lg border border-white/10 bg-[#11151a] shadow-2xl shadow-black/20">
      <div className="border-b border-white/10 px-6 py-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-cyan-300">
              One-to-one outbound
            </p>
            <h2 className="mt-1 text-2xl font-semibold text-white">Call Composer</h2>
          </div>
          <Sparkles className="h-5 w-5 text-cyan-300" />
        </div>
      </div>

      <form onSubmit={handleDispatch} className="space-y-5 p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Phone Number" icon={Phone}>
            <input
              type="tel"
              placeholder="+919876543210"
              required
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              className="field-control"
            />
          </Field>

          <Field label="Customer Name" icon={UserCheck}>
            <input
              type="text"
              placeholder="Optional"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              className="field-control"
            />
          </Field>
        </div>

        <Field label="Outbound Facility" icon={CalendarClock}>
          <select
            value={campaignType}
            onChange={(e) => handleTemplateChange(e.target.value)}
            className="field-control"
          >
            {campaignTemplates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Agent Instructions" icon={MessageSquare}>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="field-control min-h-32 resize-none"
          />
        </Field>

        <Field label="Human Transfer Number" icon={Headphones}>
          <input
            type="tel"
            placeholder="+91 sales/support line"
            value={transferNumber}
            onChange={(e) => setTransferNumber(e.target.value)}
            className="field-control"
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Model Provider">
            <select className="field-control" name="modelProvider" defaultValue="openai">
              <option value="openai">OpenAI (GPT-4o)</option>
              <option value="groq">Groq (Llama 3)</option>
            </select>
          </Field>
          <Field label="Voice">
            <select className="field-control" name="voice" defaultValue="alloy">
              <option value="alloy">Alloy (US)</option>
              <option value="echo">Echo (US)</option>
              <option value="shimmer">Shimmer (US)</option>
              <option value="anushka">Anushka (Indian - Sarvam)</option>
              <option value="aravind">Aravind (Indian - Sarvam)</option>
            </select>
          </Field>
        </div>

        <div className="rounded-md border border-cyan-300/20 bg-cyan-300/10 p-3 text-xs leading-5 text-cyan-100">
          Selected flow: {selectedTemplate?.label}. The agent receives the call objective, customer context, and transfer number as room metadata.
        </div>

        <button
          type="submit"
          disabled={status === "loading"}
          className="flex h-12 w-full items-center justify-center gap-2 rounded-md bg-cyan-500 px-5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {status === "loading" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" /> Dispatching
            </>
          ) : (
            <>
              <Phone className="h-4 w-4" /> Initiate Outbound Call
            </>
          )}
        </button>

        {message && (
          <div
            className={`flex items-center gap-2 rounded-md border p-3 text-sm ${
              status === "success"
                ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-100"
                : "border-red-400/20 bg-red-400/10 text-red-100"
            }`}
          >
            {status === "success" ? <CheckCircle2 className="h-4 w-4" /> : <TriangleAlert className="h-4 w-4" />}
            {message}
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
  icon?: typeof Phone;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-2">
      <span className="flex items-center gap-2 text-sm font-medium text-zinc-300">
        {Icon ? <Icon className="h-4 w-4 text-zinc-500" /> : null}
        {label}
      </span>
      {children}
    </label>
  );
}
