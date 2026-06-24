import { Check, FileUp, Megaphone, Rocket, Settings2, UserRoundCheck } from "lucide-react";
import { useState } from "react";
import Modal from "../components/Modal";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { agents, campaigns } from "../data/mockData";

const steps = [
  { label: "Upload CSV contacts", icon: FileUp },
  { label: "Select AI agent", icon: UserRoundCheck },
  { label: "Configure dialing", icon: Settings2 },
  { label: "Launch campaign", icon: Rocket },
];

export default function Campaigns() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Campaigns</h1>
          <p className="mt-2 text-sm text-gray-500">Plan, configure, and launch outbound calling campaigns.</p>
        </div>
        <Button onClick={() => setOpen(true)}><Megaphone className="h-4 w-4" /> Create campaign</Button>
      </div>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {campaigns.map((campaign) => (
          <article key={campaign.id} className="panel rounded-3xl p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-gray-950">{campaign.name}</h2>
                <p className="mt-1 text-sm text-gray-500">{campaign.audience}</p>
              </div>
              <Badge tone={campaign.status === "Running" ? "success" : campaign.status === "Draft" ? "neutral" : "dark"}>{campaign.status}</Badge>
            </div>
            <div className="mt-6 space-y-4">
              <Progress label="Contacts" value={campaign.contacts.toLocaleString()} />
              <Progress label="Calls completed" value={campaign.completed.toLocaleString()} />
              <div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Success rate</span>
                  <span className="font-medium text-gray-950">{campaign.success}%</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-gray-100">
                  <div className="h-2 rounded-full bg-gray-950" style={{ width: `${campaign.success}%` }} />
                </div>
              </div>
            </div>
          </article>
        ))}
      </section>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Create outbound campaign"
        description="Follow the guided campaign setup before launching calls."
        footer={
          <div className="flex justify-between">
            <Button variant="secondary" disabled={step === 0} onClick={() => setStep((value) => value - 1)}>Back</Button>
            <Button onClick={() => (step === steps.length - 1 ? setOpen(false) : setStep((value) => value + 1))}>{step === steps.length - 1 ? "Launch campaign" : "Continue"}</Button>
          </div>
        }
      >
        <div className="mb-6 grid gap-3 sm:grid-cols-4">
          {steps.map((item, index) => (
            <div key={item.label} className={`rounded-2xl border p-3 ${index <= step ? "border-gray-950 bg-gray-950 text-white" : "border-gray-200 bg-gray-50 text-gray-500"}`}>
              <item.icon className="h-4 w-4" />
              <p className="mt-2 text-xs font-medium">{item.label}</p>
            </div>
          ))}
        </div>
        {step === 0 && <StepPanel title="Upload CSV contacts"><div className="grid min-h-40 place-items-center rounded-3xl border border-dashed border-gray-300 bg-gray-50 text-center"><div><FileUp className="mx-auto h-8 w-8 text-gray-400" /><p className="mt-3 text-sm font-medium text-gray-950">Drop CSV file here</p><p className="text-sm text-gray-500">Name, phone, email, company columns supported</p></div></div></StepPanel>}
        {step === 1 && <StepPanel title="Select AI agent"><div className="grid gap-3">{agents.map((agent) => <label key={agent.id} className="flex items-center justify-between rounded-2xl border border-gray-200 p-4"><span><span className="font-medium text-gray-950">{agent.name}</span><span className="ml-2 text-sm text-gray-500">{agent.purpose}</span></span><input type="radio" name="agent" defaultChecked={agent.id === 1} /></label>)}</div></StepPanel>}
        {step === 2 && <StepPanel title="Configure campaign"><div className="grid gap-4 sm:grid-cols-3"><Field label="Calling hours" value="09:00 - 18:00" /><Field label="Retry attempts" value="3" /><Field label="Call priority" value="High" /></div></StepPanel>}
        {step === 3 && <StepPanel title="Ready to launch"><div className="rounded-3xl bg-emerald-50 p-5 text-emerald-800"><Check className="h-5 w-5" /><p className="mt-2 font-medium">Campaign validation passed. 2,480 contacts are ready for outbound calling.</p></div></StepPanel>}
      </Modal>
    </div>
  );
}

function Progress({ label, value }) {
  return <div className="flex justify-between text-sm"><span className="text-gray-500">{label}</span><span className="font-medium text-gray-950">{value}</span></div>;
}

function StepPanel({ title, children }) {
  return <section><h3 className="mb-3 text-base font-semibold text-gray-950">{title}</h3>{children}</section>;
}

function Field({ label, value }) {
  return <label className="space-y-2"><span className="text-sm font-medium text-gray-700">{label}</span><input className="field" defaultValue={value} /></label>;
}
