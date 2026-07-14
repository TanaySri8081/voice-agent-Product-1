import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bot, Settings as SettingsIcon } from "lucide-react";
import api from "../lib/api";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

export default function Agents() {
  const [clinic, setClinic] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/clinics/settings")
      .then((res) => { if (res.data?.success) setClinic(res.data.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const c = clinic || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">AI Agent</h1>
          <p className="mt-2 text-sm text-gray-500">Your clinic's inbound AI receptionist configuration.</p>
        </div>
        <Link to="/settings">
          <Button variant="secondary"><SettingsIcon className="h-4 w-4" /> Edit in Settings</Button>
        </Link>
      </div>

      <article className="panel max-w-2xl rounded-3xl p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gray-950 text-white">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-950">{loading ? "…" : (c.name || "AI Receptionist")}</h2>
              <p className="text-sm text-gray-500">Inbound appointment-booking agent</p>
            </div>
          </div>
          <Badge tone="success">Active</Badge>
        </div>

        <div className="mt-6 space-y-3 text-sm">
          <Row label="Voice" value={c.voice || "Platform default"} />
          <Row label="Language" value={c.language || "Platform default"} />
          <Row label="Model" value={c.llm_model || "Platform default"} />
          <Row label="Inbound number" value={c.did || "Not set"} />
          <Row label="Transfer to" value={c.transfer_number || "Not set"} />
        </div>

        <div className="mt-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Greeting</p>
          <p className="mt-1 text-sm text-gray-700">{c.initial_greeting || "Using the platform default greeting."}</p>
        </div>
      </article>
    </div>
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
