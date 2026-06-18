import { Save, Settings2, Sliders, KeyRound, Bell } from "lucide-react";
import { Button } from "../components/ui/Button";

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Settings</h1>
        <p className="mt-2 text-sm text-gray-500">Configure your outbound platform, integrations, and default voice behaviours.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <section className="panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <Settings2 className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-950">Project Profile</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Workspace Name</label>
              <input
                type="text"
                defaultValue="VoxPilot Voice Command Center"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Outbound Webhook URL</label>
              <input
                type="url"
                defaultValue="https://api.voxpilot.ai/v1/webhooks/call-status"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              />
            </div>
          </div>
        </section>

        <section className="panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <KeyRound className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-950">API keys & Integrations</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">LiveKit API Key</label>
              <input
                type="password"
                defaultValue="••••••••••••••••"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">OpenAI API Key</label>
              <input
                type="password"
                defaultValue="••••••••••••••••"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              />
            </div>
          </div>
        </section>

        <section className="panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <Sliders className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-950">Default Call Behaviors</h2>
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">Max Call Duration (seconds)</label>
              <input
                type="number"
                defaultValue="600"
                className="mt-1 w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              />
            </div>
            <div className="flex items-center justify-between py-2">
              <div>
                <p className="text-sm font-medium text-gray-950">Answering Machine Detection (AMD)</p>
                <p className="text-xs text-gray-500">Hang up automatically on voicemail/beeps</p>
              </div>
              <input type="checkbox" defaultChecked className="h-4 w-4 rounded border-gray-300 text-gray-950 focus:ring-gray-950" />
            </div>
          </div>
        </section>

        <section className="panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
            <Bell className="h-5 w-5 text-gray-500" />
            <h2 className="text-lg font-semibold text-gray-950">Notifications</h2>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-1">
              <div>
                <p className="text-sm font-medium text-gray-950">Email summary reports</p>
                <p className="text-xs text-gray-500">Receive daily campaign conversion logs</p>
              </div>
              <input type="checkbox" defaultChecked className="h-4 w-4 rounded border-gray-300 text-gray-950 focus:ring-gray-950" />
            </div>
            <div className="flex items-center justify-between py-1">
              <div>
                <p className="text-sm font-medium text-gray-950">Slack escalation alerts</p>
                <p className="text-xs text-gray-500">Ping channel on human escalation request</p>
              </div>
              <input type="checkbox" className="h-4 w-4 rounded border-gray-300 text-gray-950 focus:ring-gray-950" />
            </div>
          </div>
        </section>
      </div>

      <div className="flex justify-end gap-3">
        <Button variant="secondary">Cancel</Button>
        <Button><Save className="h-4 w-4" /> Save Settings</Button>
      </div>
    </div>
  );
}
