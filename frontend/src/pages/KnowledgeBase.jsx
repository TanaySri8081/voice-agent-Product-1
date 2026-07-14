import { useEffect, useState } from "react";
import { Save, BookOpen, Sparkles } from "lucide-react";
import api from "../lib/api";
import { Button } from "../components/ui/Button";

const PLACEHOLDER = `Describe your business so the AI receptionist can answer callers accurately. For example:

• Services offered (e.g. general dentistry, teeth cleaning, root canal)
• Business / clinic hours and days open
• Address and parking / directions
• Pricing or consultation fees
• Insurance accepted
• Booking and cancellation policy
• Common FAQs (e.g. "Do you take walk-ins?")`;

function extractError(err) {
  const d = err?.response?.data;
  if (d) {
    if (d.message) return d.message;
    if (typeof d.error === "string" && d.error) return d.error;
    if (d.detail) {
      if (Array.isArray(d.detail)) {
        return d.detail.map((x) => `${x.loc?.[x.loc.length - 1]}: ${x.msg}`).join(", ");
      }
      return d.detail;
    }
  }
  if (err?.response?.status === 503) return "Database is not configured on the server.";
  return "Could not reach the server.";
}

export default function KnowledgeBase() {
  const [knowledge, setKnowledge] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null); // { type, text }

  useEffect(() => {
    let active = true;
    api
      .get("/clinics/settings")
      .then((res) => {
        if (active && res.data && res.data.success) {
          setKnowledge(res.data.data.knowledge_base || "");
        }
      })
      .catch((err) => {
        if (active) setStatus({ type: "error", text: extractError(err) });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const res = await api.put("/clinics/settings", { knowledge_base: knowledge });
      if (res.data && res.data.success) {
        setStatus({ type: "success", text: "Knowledge base saved. The AI receptionist will use it on the next call." });
      } else {
        setStatus({ type: "error", text: (res.data && res.data.message) || "Could not save." });
      }
    } catch (err) {
      setStatus({ type: "error", text: extractError(err) });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Knowledge Base</h1>
          <p className="mt-2 text-sm text-gray-500">
            Enter your business details. The AI receptionist uses this to answer callers and book appointments accurately.
          </p>
        </div>
        <Button onClick={handleSave} disabled={loading || saving}>
          <Save className="h-4 w-4" /> {saving ? "Saving..." : "Save"}
        </Button>
      </div>

      {status && (
        <div
          className={`rounded-2xl border p-4 text-sm ${
            status.type === "success"
              ? "border-emerald-100 bg-emerald-50 text-emerald-800"
              : "border-red-100 bg-red-50 text-red-800"
          }`}
        >
          {status.text}
        </div>
      )}

      <section className="panel rounded-3xl border border-gray-100 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-2 border-b border-gray-100 pb-3">
          <BookOpen className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-950">Business information</h2>
        </div>

        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500">
          What should the AI know about your business?
        </label>
        <textarea
          rows={16}
          className="mt-2 w-full rounded-2xl border border-gray-200 p-4 text-sm leading-6 focus:border-gray-950 focus:outline-none"
          placeholder={PLACEHOLDER}
          value={knowledge}
          onChange={(event) => setKnowledge(event.target.value)}
          disabled={loading}
        />

        <p className="mt-3 flex items-center gap-2 text-xs text-gray-400">
          <Sparkles className="h-3.5 w-3.5" />
          Tip: write it like you'd brief a new receptionist. Plain text and bullet points work great.
        </p>
      </section>
    </div>
  );
}
