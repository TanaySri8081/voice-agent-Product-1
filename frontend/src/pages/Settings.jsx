import React, { useState, useEffect } from "react";
import { Save, Settings2, Sliders, KeyRound, Bell, MessageSquareCode } from "lucide-react";
import { Button } from "../components/ui/Button";
import axios from "axios";

export default function Settings() {
  const [clinicName, setClinicName] = useState("VoxPilot Voice Command Center");
  const [did, setDid] = useState("+918045671200");
  const [transferNumber, setTransferNumber] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [initialGreeting, setInitialGreeting] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [statusType, setStatusType] = useState(""); // success or error

  useEffect(() => {
    setLoading(true);
    axios.get("http://localhost:8002/api/clinics/settings")
      .then(res => {
        if (res.data && res.data.success) {
          const d = res.data.data;
          setClinicName(d.name || "");
          setDid(d.did || "");
          setTransferNumber(d.transfer_number || "");
          setSystemPrompt(d.system_prompt || "");
          setInitialGreeting(d.initial_greeting || "");
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
    
    axios.put("http://localhost:8002/api/clinics/settings", {
      name: clinicName,
      did: did,
      transfer_number: transferNumber,
      system_prompt: systemPrompt,
      initial_greeting: initialGreeting
    })
      .then(res => {
        if (res.data && res.data.success) {
          setStatusMsg("Settings saved successfully!");
          setStatusType("success");
        } else {
          setStatusMsg(res.data.message || "Failed to save settings.");
          setStatusType("error");
        }
      })
      .catch(err => {
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
        <p className="mt-2 text-sm text-gray-500">Configure your outbound platform, integrations, and default voice behaviours.</p>
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
            <h2 className="text-lg font-semibold text-gray-950">Project Profile</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Clinic Name</label>
              <input
                type="text"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
                value={clinicName}
                onChange={(e) => setClinicName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Vobiz DID inbound phone number</label>
              <input
                type="text"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
                value={did}
                onChange={(e) => setDid(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Default Transfer Number (SIP / Phone)</label>
              <input
                type="text"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
                placeholder="+91XXXXXXXXXX"
                value={transferNumber}
                onChange={(e) => setTransferNumber(e.target.value)}
              />
            </div>
          </div>
        </section>

        <section className="panel rounded-3xl p-6 space-y-4 border border-gray-100 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <MessageSquareCode className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-950">AI Receptionist Customization</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Initial Greeting Voice Message</label>
              <input
                type="text"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
                value={initialGreeting}
                onChange={(e) => setInitialGreeting(e.target.value)}
                placeholder="Hello! Thank you for calling Apex Clinic. Dr. Raj is currently in session. How may I assist you today?"
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
      </div>

      <div className="flex justify-end gap-3">
        <Button variant="secondary">Cancel</Button>
        <Button onClick={handleSave} disabled={loading}>
          <Save className="h-4 w-4" /> 
          {loading ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </div>
  );
}
