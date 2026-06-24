import {
  BarChart3,
  BellRing,
  CalendarClock,
  ClipboardCheck,
  CreditCard,
  Headphones,
  Megaphone,
  MessageSquareText,
  PackageCheck,
  PhoneCall,
  RadioTower,
  Star,
  TrendingUp,
  Users,
} from "lucide-react";
import BulkDialer from "@/components/BulkDialer";
import CallDispatcher from "@/components/CallDispatcher";
import InboundConsole from "@/components/InboundConsole";

const facilities = [
  { label: "Campaigns", detail: "Marketing, reminders, win-backs", icon: Megaphone },
  { label: "Appointments", detail: "Confirm, reschedule, cancel", icon: CalendarClock },
  { label: "Lead Qualification", detail: "Score interest and urgency", icon: ClipboardCheck },
  { label: "Billing", detail: "Due reminders and promise-to-pay", icon: CreditCard },
  { label: "Feedback", detail: "Ratings after service or purchase", icon: Star },
  { label: "Delivery Updates", detail: "Order and shipment notifications", icon: PackageCheck },
  { label: "Surveys", detail: "Research calls with structured answers", icon: MessageSquareText },
  { label: "Human Transfer", detail: "Escalate when intent is hot", icon: Headphones },
];

const stats = [
  { label: "Outbound modes", value: "8", note: "Ready templates", icon: RadioTower },
  { label: "Queue controls", value: "CSV", note: "Bulk launch", icon: Users },
  { label: "Transfer path", value: "Live", note: "Human handoff metadata", icon: PhoneCall },
  { label: "Response capture", value: "CRM", note: "Structured call context", icon: BarChart3 },
];

const workflow = [
  "Verify identity",
  "Deliver message",
  "Capture response",
  "Update records",
  "Transfer when needed",
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0b0d10] text-zinc-100">
      <div className="border-b border-white/10 bg-[#11151a]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="inline-flex items-center gap-2 rounded-md border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-300" />
                Outbound agent system online
              </div>
              <h1 className="mt-4 text-3xl font-semibold tracking-normal text-white md:text-5xl">
                Rapid X AI Outbound Console
              </h1>
              <p className="mt-3 max-w-3xl text-base leading-7 text-zinc-400">
                Initiate customer calls, launch bulk campaigns, route qualified leads to humans, and keep inbound readiness visible from one operations surface.
              </p>
            </div>
            <div className="grid min-w-0 grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[520px]">
              {stats.map((stat) => (
                <div key={stat.label} className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
                  <div className="flex items-center justify-between gap-2">
                    <stat.icon className="h-4 w-4 text-cyan-300" />
                    <span className="text-xl font-semibold text-white">{stat.value}</span>
                  </div>
                  <p className="mt-3 text-xs font-medium text-zinc-300">{stat.label}</p>
                  <p className="mt-1 text-xs text-zinc-500">{stat.note}</p>
                </div>
              ))}
            </div>
          </div>

          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {facilities.map((item) => (
              <div key={item.label} className="rounded-lg border border-white/10 bg-[#0c1015] p-4">
                <div className="flex items-start gap-3">
                  <div className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-cyan-400/10 text-cyan-200">
                    <item.icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white">{item.label}</p>
                    <p className="mt-1 text-xs leading-5 text-zinc-500">{item.detail}</p>
                  </div>
                </div>
              </div>
            ))}
          </section>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_360px] lg:px-8">
        <section className="grid gap-6 xl:grid-cols-2">
          <CallDispatcher />
          <BulkDialer />
        </section>

        <aside className="space-y-6">
          <div className="rounded-lg border border-white/10 bg-[#11151a] p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-amber-300">
                  Call workflow
                </p>
                <h2 className="mt-1 text-xl font-semibold text-white">Outbound Runbook</h2>
              </div>
              <TrendingUp className="h-5 w-5 text-amber-300" />
            </div>
            <div className="mt-5 space-y-3">
              {workflow.map((step, index) => (
                <div key={step} className="flex items-center gap-3 rounded-md border border-white/10 bg-white/[0.03] p-3">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-amber-300/10 text-xs font-semibold text-amber-200">
                    {index + 1}
                  </span>
                  <span className="text-sm text-zinc-300">{step}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-[#11151a] p-5">
            <div className="flex items-center gap-3">
              <BellRing className="h-5 w-5 text-rose-300" />
              <div>
                <p className="text-sm font-medium text-white">Escalation policy</p>
                <p className="mt-1 text-xs leading-5 text-zinc-500">
                  Transfer leads with purchase intent, billing disputes, cancellation risk, or failed identity verification.
                </p>
              </div>
            </div>
          </div>
        </aside>
      </div>

      <div className="mx-auto w-full max-w-7xl px-4 pb-8 sm:px-6 lg:px-8">
        <InboundConsole />
      </div>
    </main>
  );
}
