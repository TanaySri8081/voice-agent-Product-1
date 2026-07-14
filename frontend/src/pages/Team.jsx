import { useEffect, useState, useCallback } from "react";
import { UserPlus, Copy, Check } from "lucide-react";
import api from "../lib/api";
import DataTable from "../components/DataTable";
import Modal from "../components/Modal";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

const ROLES = ["doctor", "admin", "receptionist"];
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

export default function Team() {
  const [me, setMe] = useState({ id: null, role: "" });
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "receptionist" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [copied, setCopied] = useState(false);

  const isManager = MANAGER_ROLES.includes(me.role);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [meRes, teamRes] = await Promise.all([api.get("/auth/me"), api.get("/team/")]);
      if (meRes.data?.success) setMe({ id: meRes.data.data.id, role: meRes.data.data.role });
      setMembers(teamRes.data?.success ? teamRes.data.data || [] : []);
    } catch {
      setMembers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const invite = async () => {
    setFormError("");
    setInviteLink("");
    if (!form.name.trim() || !form.email.trim()) {
      setFormError("Name and email are required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post("/team/", { name: form.name.trim(), email: form.email.trim(), role: form.role });
      if (res.data?.success) {
        setInviteLink(res.data.data?.invite_link || "");
        setForm({ name: "", email: "", role: "receptionist" });
        load();
      } else {
        setFormError(res.data?.message || "Could not invite member.");
      }
    } catch (err) {
      setFormError(extractError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const changeRole = async (row, role) => {
    setBanner(null);
    setBusyId(row.id);
    try {
      const res = await api.put(`/team/${row.id}/role`, { role });
      if (res.data?.success) {
        setMembers((prev) => prev.map((m) => (m.id === row.id ? { ...m, role } : m)));
      } else {
        setBanner({ type: "error", text: res.data?.message || "Could not update role." });
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
      const res = await api.delete(`/team/${row.id}`);
      if (res.data?.success) {
        setBanner({ type: "success", text: `Removed ${row.name}.` });
        load();
      } else {
        setBanner({ type: "error", text: res.data?.message || "Could not remove member." });
      }
    } catch (err) {
      setBanner({ type: "error", text: extractError(err) });
    } finally {
      setBusyId(null);
    }
  };

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(inviteLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard may be blocked; the link is visible to copy manually */
    }
  };

  const columns = [
    { key: "name", header: "Name" },
    { key: "email", header: "Email" },
    {
      key: "role",
      header: "Role",
      render: (row) =>
        isManager ? (
          <select
            className="rounded-lg border border-gray-200 px-2 py-1 text-sm capitalize focus:border-gray-950 focus:outline-none"
            value={row.role}
            disabled={busyId === row.id}
            onChange={(e) => changeRole(row, e.target.value)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        ) : (
          <Badge tone="neutral">{row.role}</Badge>
        ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) =>
        isManager && row.id !== me.id ? (
          <Button variant="danger" size="sm" disabled={busyId === row.id} onClick={() => remove(row)}>
            {busyId === row.id ? "..." : "Remove"}
          </Button>
        ) : (
          <span className="text-xs text-gray-400">{row.id === me.id ? "You" : "—"}</span>
        ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-gray-950">Team</h1>
          <p className="mt-2 text-sm text-gray-500">Invite teammates to your clinic and manage their roles.</p>
        </div>
        {isManager && (
          <Button onClick={() => { setFormError(""); setInviteLink(""); setForm({ name: "", email: "", role: "receptionist" }); setOpen(true); }}>
            <UserPlus className="h-4 w-4" /> Invite member
          </Button>
        )}
      </div>

      {banner && (
        <div className={`flex items-start justify-between gap-3 rounded-2xl border p-4 text-sm ${banner.type === "success" ? "border-emerald-100 bg-emerald-50 text-emerald-800" : "border-red-100 bg-red-50 text-red-800"}`}>
          <span>{banner.text}</span>
          <button className="text-xs font-medium opacity-70 hover:opacity-100" onClick={() => setBanner(null)}>Dismiss</button>
        </div>
      )}

      <DataTable columns={columns} rows={members} loading={loading} emptyTitle="No team members yet" />

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Invite team member"
        description="They'll get a secure link to set their own password."
        footer={
          <div className="flex justify-end gap-3">
            <Button variant="secondary" onClick={() => setOpen(false)}>Close</Button>
            <Button onClick={invite} disabled={submitting}>{submitting ? "Inviting..." : "Send invite"}</Button>
          </div>
        }
      >
        {formError && <div className="mb-4 rounded-2xl border border-red-100 bg-red-50 p-3 text-sm text-red-800">{formError}</div>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Labeled label="Name">
            <input className="w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Jane Doe" />
          </Labeled>
          <Labeled label="Email">
            <input type="email" className="w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm focus:border-gray-950 focus:outline-none" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} placeholder="Email address" />
          </Labeled>
          <Labeled label="Role">
            <select className="w-full rounded-xl border border-gray-200 px-3.5 py-2 text-sm capitalize focus:border-gray-950 focus:outline-none" value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}>
              <option value="receptionist">receptionist</option>
              <option value="admin">admin</option>
            </select>
          </Labeled>
        </div>

        {inviteLink && (
          <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
            <p className="text-sm font-medium text-emerald-800">Invite created. Share this link so they can set their password:</p>
            <div className="mt-2 flex gap-2">
              <input readOnly value={inviteLink} className="w-full rounded-xl border border-emerald-200 bg-white px-3 py-2 text-xs text-gray-700" />
              <Button variant="secondary" size="sm" onClick={copyLink}>
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />} {copied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

function Labeled({ label, children }) {
  return (
    <label className="space-y-1.5 block">
      <span className="block text-xs font-semibold uppercase tracking-wider text-gray-500">{label}</span>
      {children}
    </label>
  );
}
