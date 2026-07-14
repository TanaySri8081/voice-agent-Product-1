import { CalendarPlus } from "lucide-react";
import { useMemo, useState, useEffect, useCallback } from "react";
import api from "../lib/api";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

const emptyForm = { patient_name: "", appointment_date: "", reason: "" };

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

const statusTone = (status) => {
  switch (status) {
    case "completed":
      return "success";
    case "cancelled":
      return "danger";
    case "scheduled":
      return "warning";
    default:
      return "neutral";
  }
};

export default function Appointments() {
  const [list, setList] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const [banner, setBanner] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const loadAppointments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/appointments/");
      if (res.data && res.data.success) {
        setList(res.data.data || []);
        setLive(true);
      } else {
        setList([]);
        setLive(false);
      }
    } catch {
      setList([]);
      setLive(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAppointments();
  }, [loadAppointments]);

  const filtered = useMemo(
    () =>
      list.filter((a) =>
        `${a.patient_name} ${a.reason || ""} ${a.status}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [query, list],
  );

  const updateField = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const submitAppointment = async () => {
    setFormError("");
    if (!form.patient_name.trim() || !form.appointment_date.trim()) {
      setFormError("Patient name and date/time are required.");
      return;
    }
    const payload = {
      patient_id: "manual",
      patient_name: form.patient_name.trim(),
      appointment_date: form.appointment_date.trim(),
      reason: form.reason.trim() || null,
      status: "scheduled",
    };
    setSubmitting(true);
    try {
      const res = await api.post("/appointments/", payload);
      if (res.data && res.data.success) {
        setOpen(false);
        setForm(emptyForm);
        setBanner({ type: "success", text: `Appointment booked for ${payload.patient_name}.` });
        loadAppointments();
      } else {
        setFormError((res.data && res.data.message) || "Could not book the appointment.");
      }
    } catch (err) {
      setFormError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const cancelAppointment = async (row) => {
    setBanner(null);
    setBusyId(row.id);
    try {
      const res = await api.delete(`/appointments/${row.id}`);
      if (res.data && res.data.success) {
        setBanner({ type: "success", text: `Cancelled appointment for ${row.patient_name}.` });
        loadAppointments();
      } else {
        setBanner({ type: "error", text: (res.data && res.data.message) || "Could not cancel." });
      }
    } catch (err) {
      setBanner({ type: "error", text: extractError(err) });
    } finally {
      setBusyId(null);
    }
  };

  const columns = [
    { key: "patient_name", header: "Patient" },
    { key: "appointment_date", header: "When" },
    { key: "reason", header: "Reason", render: (row) => row.reason || "—" },
    {
      key: "status",
      header: "Status",
      render: (row) => <Badge tone={statusTone(row.status)}>{row.status}</Badge>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) =>
        row.status === "cancelled" ? (
          <span className="text-xs text-gray-400">—</span>
        ) : (
          <Button variant="secondary" size="sm" disabled={busyId === row.id} onClick={() => cancelAppointment(row)}>
            {busyId === row.id ? "Cancelling..." : "Cancel"}
          </Button>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Appointments</h1>
          <p className="mt-2 text-sm text-gray-500">Appointments booked by the AI receptionist and your team.</p>
        </div>
        <Button onClick={() => { setFormError(""); setForm(emptyForm); setOpen(true); }}>
          <CalendarPlus className="h-4 w-4" /> Book appointment
        </Button>
      </div>

      {banner && (
        <div
          className={`flex items-start justify-between gap-3 rounded-2xl border p-4 text-sm ${
            banner.type === "success"
              ? "border-emerald-100 bg-emerald-50 text-emerald-800"
              : "border-red-100 bg-red-50 text-red-800"
          }`}
        >
          <span>{banner.text}</span>
          <button className="text-xs font-medium opacity-70 hover:opacity-100" onClick={() => setBanner(null)}>
            Dismiss
          </button>
        </div>
      )}

      {!loading && !live && (
        <p className="text-xs text-gray-400">Couldn't reach the backend. Sign in and ensure the API is running to see live appointments.</p>
      )}

      <div className="panel flex flex-col gap-3 rounded-3xl p-4">
        <input
          className="w-full rounded-2xl border border-gray-200 px-3.5 py-2 text-sm outline-none focus:border-gray-950"
          placeholder="Search by patient, reason, or status..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <DataTable columns={columns} rows={filtered} loading={loading} emptyTitle="No appointments yet" />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Book appointment"
        description="Manually add an appointment. Patient name and date/time are required."
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={submitAppointment} disabled={submitting}>{submitting ? "Saving..." : "Book appointment"}</Button>
          </div>
        }
      >
        {formError && (
          <div className="mb-4 rounded-2xl border border-red-100 bg-red-50 p-3 text-sm text-red-800">{formError}</div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Patient name *" value={form.patient_name} onChange={updateField("patient_name")} placeholder="Jane Doe" />
          <Field label="Date & time *" type="datetime-local" value={form.appointment_date} onChange={updateField("appointment_date")} />
          <div className="sm:col-span-2">
            <Field label="Reason" value={form.reason} onChange={updateField("reason")} placeholder="Dental cleaning" />
          </div>
        </div>
      </Modal>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="space-y-1.5">
      <span className="block text-xs font-semibold uppercase tracking-wider text-gray-500">{label}</span>
      <input
        type={type}
        className="w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
      />
    </label>
  );
}
