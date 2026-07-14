import React, { useState, useEffect } from "react";
import { Save, Settings2, MessageSquareCode, AudioLines } from "lucide-react";
import { Button } from "../components/ui/Button";
import api from "../lib/api";

const LANGUAGES = [
  { code: "hi", label: "Hindi" },
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "pt", label: "Portuguese" },
  { code: "it", label: "Italian" },
  { code: "nl", label: "Dutch" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Chinese" },
  { code: "ru", label: "Russian" },
];

export default function Settings() {
  const [clinicName, setClinicName] = useState("");
  const [did, setDid] = useState("");
  const [transferNumber, setTransferNumber] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [initialGreeting, setInitialGreeting] = useState("");
  const [voice, setVoice] = useState("");
  const [language, setLanguage] = useState("");
  const [llmModel, setLlmModel] = useState("");

  const [loading, setLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState("");
  const [statusType, setStatusType] = useState(""); // success or error

  useEffect(() => {
    api.get("/clinics/settings")
      .then(res => {
        if (res.data && res.data.success) {
          const d = res.data.data;
          setClinicName(d.name || "");
          setDid(d.did || "");
          setTransferNumber(d.transfer_number || "");
          setSystemPrompt(d.system_prompt || "");
          setInitialGreeting(d.initial_greeting || "");
          setVoice(d.voice || "");
          setLanguage(d.language || "hi");
          setLlmModel(d.llm_model || "");
        }
      })
      .catch(err => {
        console.error("Failed to load clinic settings from API:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleSave = () => {
    setLoading(true);
    setStatusMsg("");

    api.put("/clinics/settings", {
      name: clinicName,
      did: did,
      transfer_number: transferNumber,
      system_prompt: systemPrompt,
      initial_greeting: initialGreeting,
      voice: voice,
      language: language,
      llm_model: llmModel,
    })
      .then(res => {
        if (res.data && res.data.success) {
          setStatusMsg("Settings saved. Changes apply on the next call.");
          setStatusType("success");
        } else {
          setStatusMsg(res.data.message || "Failed to save settings.");
          setStatusType("error");
        }
      })
      .catch(() => {
        setStatusMsg("Failed to connect to the server.");
        setStatusType("error");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Settings</h1>
        <p className="mt-2 text-sm text-gray-500">Configure your clinic profile and how your AI receptionist sounds and behaves.</p>
      </div>

      {statusMsg && (
        <div className={`rounded-2xl p-4 text-sm border ${
          statusType === "success"
            ? "bg-emerald-50 text-emerald-800 border-emerald-100"
            : "bg-red-50 text-red-800 border-red-100"
        }`}>
          {statusMsg}
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <section className="panel rounded-3xl p-6 space-y-4 border border-gray-100 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <Settings2 className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-950">Clinic Profile</h2>
          </div>
          <div className="space-y-3">
            <Field label="Clinic Name" value={clinicName} onChange={setClinicName} />
            <Field label="Vobiz DID inbound phone number" value={did} onChange={setDid} placeholder="+918045671200" />
            <Field label="Default Transfer Number (SIP / Phone)" value={transferNumber} onChange={setTransferNumber} placeholder="+91XXXXXXXXXX" />
          </div>
        </section>

        <section className="panel rounded-3xl p-6 space-y-4 border border-gray-100 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <AudioLines className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-950">Voice & Language</h2>
          </div>
          <div className="space-y-3">
            <Field label="Voice" value={voice} onChange={setVoice} placeholder="e.g. male-qn-qingse" hint="The TTS voice your receptionist speaks with." />
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500">Language</label>
              <select
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
                value={language || "hi"}
                onChange={(e) => setLanguage(e.target.value)}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">The language your callers speak — drives transcription and the agent's voice.</p>
            </div>
            <Field label="AI Model" value={llmModel} onChange={setLlmModel} placeholder="e.g. abab6.5g-chat" hint="The language model powering the conversation." />
          </div>
        </section>
      </div>

      <section className="panel rounded-3xl p-6 space-y-4 border border-gray-100 bg-white shadow-sm">
        <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
          <MessageSquareCode className="h-5 w-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-950">AI Receptionist Behaviour</h2>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Initial Greeting</label>
            <input
              type="text"
              className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              value={initialGreeting}
              onChange={(e) => setInitialGreeting(e.target.value)}
              placeholder="Greet the caller warmly and ask how you can help them book an appointment."
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">AI System Prompt (Instructions)</label>
            <textarea
              rows={5}
              className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are an AI receptionist for a dental clinic..."
            />
          </div>
        </div>
      </section>

      <div className="flex justify-end gap-3">
        <Button onClick={handleSave} disabled={loading}>
          <Save className="h-4 w-4" />
          {loading ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, hint }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</label>
      <input
        type="text"
        className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {hint && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
    </div>
  );
}
