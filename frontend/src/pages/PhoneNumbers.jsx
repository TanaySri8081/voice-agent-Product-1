import { useEffect, useState, useCallback } from "react";
import { Plus, PhoneCall } from "lucide-react";
import api from "../lib/api";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

const MANAGER_ROLES = ["doctor", "admin"];

function extractError(err) {
  const d = err?.response?.data;
  if (d?.message) return d.message;
  if (typeof d?.error === "string" && d.error) return d.error;
  if (d?.detail) {
    if (Array.isArray(d.detail)) return d.detail.map((x) => `${x.loc?.[x.loc.length - 1]}: ${x.msg}`).join(", ");
    return d.detail;
  }
  return "Could not reach the server.";
}

export default function PhoneNumbers() {
  const [role, setRole] = useState("");
  const [numbers, setNumbers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ number: "", label: "" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const isManager = MANAGER_ROLES.includes(role);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [meRes, listRes] = await Promise.all([api.get("/auth/me"), api.get("/phone-numbers/")]);
      if (meRes.data?.success) setRole(meRes.data.data.role || "");
      setNumbers(listRes.data?.success ? listRes.data.data || [] : []);
    } catch {
      setNumbers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const connect = async () => {
    setFormError("");
    if (!form.number.trim()) {
      setFormError("Enter the phone number you want to connect.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post("/phone-numbers/", { number: form.number.trim(), label: form.label.trim() || null });
      if (res.data?.success) {
        setOpen(false);
        setForm({ number: "", label: "" });
        setBanner({ type: "success", text: "Number connected. Point its provider webhook at your VoxPilot inbound URL to receive calls." });
        load();
      } else {
        setFormError(res.data?.message || "Could not connect the number.");
      }
    } catch (err) {
      setFormError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleStatus = async (row) => {
    setBanner(null);
    setBusyId(row.id);
    const next = row.status === "active" ? "inactive" : "active";
    try {
      const res = await api.put(`/phone-numbers/${row.id}`, { status: next });
      if (res.data?.success) {
        setNumbers((prev) => prev.map((n) => (n.id === row.id ? { ...n, status: next } : n)));
      } else {
        setBanner({ type: "error", text: res.data?.message || "Could not update the number." });
      }
    } catch (err) {
      setBanner({ type: "error", text: extractError(err) });
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (row) => {
    setBanner(null);
    setBusyId(row.id);
    try {
      const res = await api.delete(`/phone-numbers/${row.id}`);
      if (res.data?.success) {
        setBanner({ type: "success", text: `Removed ${row.number}.` });
        load();
      } else {
        setBanner({ type: "error", text: res.data?.message || "Could not remove the number." });
      }
    } catch (err) {
      setBanner({ type: "error", text: extractError(err) });
    } finally {
      setBusyId(null);
    }
  };

  const columns = [
    { key: "number", header: "Phone Number" },
    { key: "label", header: "Label", render: (row) => row.label || "—" },
    {
      key: "status",
      header: "Status",
      render: (row) => <Badge tone={row.status === "active" ? "success" : "neutral"}>{row.status}</Badge>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) =>
        isManager ? (
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" disabled={busyId === row.id} onClick={() => toggleStatus(row)}>
              {row.status === "active" ? "Deactivate" : "Activate"}
            </Button>
            <Button variant="danger" size="sm" disabled={busyId === row.id} onClick={() => remove(row)}>
              Remove
            </Button>
          </div>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Phone Numbers</h1>
          <p className="mt-2 text-sm text-gray-500">
            Connect the inbound numbers you own with your telephony provider. Calls to an active number are answered by your AI receptionist.
          </p>
        </div>
        {isManager && (
          <Button onClick={() => { setFormError(""); setForm({ number: "", label: "" }); setOpen(true); }}>
            <Plus className="h-4 w-4" /> Connect number
          </Button>
        )}
      </div>

      {banner && (
        <div className={`flex items-start justify-between gap-3 rounded-2xl border p-4 text-sm ${banner.type === "success" ? "border-emerald-100 bg-emerald-50 text-emerald-800" : "border-red-100 bg-red-50 text-red-800"}`}>
          <span>{banner.text}</span>
          <button className="text-xs font-medium opacity-70 hover:opacity-100" onClick={() => setBanner(null)}>Dismiss</button>
        </div>
      )}

      <DataTable columns={columns} rows={numbers} loading={loading} emptyTitle="No numbers connected yet" />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Connect a phone number"
        description="Enter a number you already own with your telephony provider."
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={connect} disabled={submitting}>{submitting ? "Connecting..." : "Connect"}</Button>
          </div>
        }
      >
        {formError && <div className="mb-4 rounded-2xl border border-red-100 bg-red-50 p-3 text-sm text-red-800">{formError}</div>}
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1.5 block">
            <span className="block text-xs font-semibold uppercase tracking-wider text-gray-500">Phone number *</span>
            <input
              className="w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              value={form.number}
              onChange={(e) => setForm((f) => ({ ...f, number: e.target.value }))}
              placeholder="+14155550100"
            />
          </label>
          <label className="space-y-1.5 block">
            <span className="block text-xs font-semibold uppercase tracking-wider text-gray-500">Label</span>
            <input
              className="w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
              value={form.label}
              onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              placeholder="Main line"
            />
          </label>
        </div>
        <p className="mt-4 flex items-start gap-2 text-xs text-gray-400">
          <PhoneCall className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          After connecting, set this number's answer webhook (at your provider) to your VoxPilot inbound URL so calls reach the AI receptionist.
        </p>
      </Modal>
    </div>
  );
}
