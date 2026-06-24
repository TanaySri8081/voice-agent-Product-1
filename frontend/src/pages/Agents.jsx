import { Bot, Edit3, Plus, Power } from "lucide-react";
import { useState } from "react";
import Modal from "../components/Modal";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { agents } from "../data/mockData";
import { compactNumber } from "../utils/format";

export default function Agents() {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-6">
      <Header title="AI Agents" description="Create, tune, and monitor voice agents for outbound workflows." action={<Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> Create AI agent</Button>} />

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {agents.map((agent) => (
          <article key={agent.id} className="panel rounded-3xl p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gray-950 text-white">
                <Bot className="h-5 w-5" />
              </div>
              <button className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${agent.active ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-500"}`}>
                <Power className="h-3 w-3" />
                {agent.active ? "Active" : "Paused"}
              </button>
            </div>
            <h2 className="mt-5 text-xl font-semibold text-gray-950">{agent.name}</h2>
            <p className="mt-1 text-sm text-gray-500">{agent.purpose}</p>
            <div className="mt-5 space-y-3 text-sm">
              <Row label="Voice" value={agent.voice} />
              <Row label="Language" value={agent.language} />
              <Row label="Industry" value={agent.industry} />
              <Row label="Calls handled" value={compactNumber(agent.calls)} />
            </div>
            <div className="mt-5 flex items-center justify-between">
              <Badge tone={agent.active ? "success" : "neutral"}>{agent.active ? "Production" : "Draft"}</Badge>
              <Button variant="secondary" size="sm"><Edit3 className="h-4 w-4" /> Edit</Button>
            </div>
          </article>
        ))}
      </section>

      <CreateAgentModal open={open} onClose={() => setOpen(false)} />
    </div>
  );
}

function CreateAgentModal({ open, onClose }) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create AI agent"
      description="Define the agent behavior, voice, and campaign objective."
      footer={<div className="flex justify-end gap-3"><Button variant="secondary" onClick={onClose}>Cancel</Button><Button onClick={onClose}>Create agent</Button></div>}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Agent Name" placeholder="Sarah" />
        <Field label="Industry" placeholder="Healthcare, SaaS, Fintech..." />
        <Field label="Voice selection" as="select" options={["Alloy", "Echo", "Shimmer", "Anushka", "Aravind"]} />
        <Field label="Language" as="select" options={["English", "Hindi", "English + Hindi", "Spanish"]} />
        <Field label="Personality" placeholder="Warm, concise, confident" />
        <Field label="Call objective" placeholder="Qualify high-intent demo leads" />
        <label className="space-y-2 sm:col-span-2">
          <span className="text-sm font-medium text-gray-700">System prompt</span>
          <textarea className="field min-h-28" placeholder="You are a helpful outbound calling assistant for ABC company..." />
        </label>
        <label className="space-y-2 sm:col-span-2">
          <span className="text-sm font-medium text-gray-700">Greeting message</span>
          <textarea className="field min-h-24" placeholder="Hi, I am Sarah from ABC company. I am calling regarding your inquiry..." />
        </label>
      </div>
    </Modal>
  );
}

function Field({ label, placeholder, as, options = [] }) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      {as === "select" ? (
        <select className="field">{options.map((option) => <option key={option}>{option}</option>)}</select>
      ) : (
        <input className="field" placeholder={placeholder} />
      )}
    </label>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-950">{value}</span>
    </div>
  );
}

function Header({ title, description, action }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">{title}</h1>
        <p className="mt-2 text-sm text-gray-500">{description}</p>
      </div>
      {action}
    </div>
  );
}
