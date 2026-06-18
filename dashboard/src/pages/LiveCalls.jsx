import { MicOff, PhoneOff, PhoneForwarded } from "lucide-react";
import { Button } from "../components/ui/Button";
import { activeCalls } from "../data/mockData";

export default function LiveCalls() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Live Call Monitoring</h1>
        <p className="mt-2 text-sm text-gray-500">Watch active AI conversations, transcripts, and escalation controls.</p>
      </div>
      <section className="grid gap-5 xl:grid-cols-3">
        {activeCalls.map((call) => (
          <article key={call.id} className="panel rounded-3xl p-5">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-950">{call.customer}</h2>
                <p className="text-sm text-gray-500">{call.agent}</p>
              </div>
              <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">Live {call.duration}</div>
            </div>
            <div className="my-6 flex h-16 items-center justify-center gap-1 rounded-3xl bg-gray-50">
              {Array.from({ length: 22 }).map((_, index) => (
                <span key={index} className="wave-bar" style={{ animationDelay: `${index * 55}ms` }} />
              ))}
            </div>
            <div className="max-h-48 space-y-3 overflow-y-auto rounded-3xl border border-gray-200 bg-white p-4">
              {call.transcript.map((line) => (
                <p key={line} className="text-sm leading-6 text-gray-600">{line}</p>
              ))}
            </div>
            <div className="mt-5 grid grid-cols-3 gap-2">
              <Button variant="secondary"><MicOff className="h-4 w-4" /> Mute</Button>
              <Button variant="secondary"><PhoneForwarded className="h-4 w-4" /> Transfer</Button>
              <Button variant="danger"><PhoneOff className="h-4 w-4" /> End</Button>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
