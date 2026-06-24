import {
  BarChart3,
  BookOpen,
  Bot,
  CreditCard,
  Gauge,
  Headphones,
  ListChecks,
  Megaphone,
  Phone,
  Settings,
  Users,
  X,
  LogOut,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

const items = [
  { label: "Dashboard", path: "/dashboard", icon: Gauge },
  { label: "AI Agents", path: "/agents", icon: Bot },
  { label: "Campaigns", path: "/campaigns", icon: Megaphone },
  { label: "Contacts", path: "/contacts", icon: Users },
  { label: "Live Calls", path: "/calls/live", icon: Headphones },
  { label: "Call Logs", path: "/call-logs", icon: ListChecks },
  { label: "Analytics", path: "/analytics", icon: BarChart3 },
  { label: "Knowledge Base", path: "/knowledge-base", icon: BookOpen },
  { label: "Phone Numbers", path: "/phone-numbers", icon: Phone },
  { label: "Billing", path: "/billing", icon: CreditCard },
  { label: "Settings", path: "/settings", icon: Settings },
];

export default function Sidebar({ open, onClose }) {
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    onClose?.();
  };

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-gray-950/35 backdrop-blur-sm transition lg:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-gray-200 bg-white/90 px-4 py-5 shadow-2xl shadow-gray-950/10 backdrop-blur-xl transition-transform lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-2xl bg-gray-950 text-white shadow-lg shadow-gray-950/20">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-950">VoxPilot AI</p>
              <p className="text-xs text-gray-500">Outbound voice ops</p>
            </div>
          </div>
          <button className="rounded-xl p-2 text-gray-500 hover:bg-gray-100 lg:hidden" onClick={onClose}>
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="mt-8 space-y-1">
          {items.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-gray-950 text-white shadow-lg shadow-gray-950/15"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-950"
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 hover:text-red-700 transition cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </nav>

        <div className="mt-auto rounded-3xl border border-gray-200 bg-gray-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-950">
            <span className="status-dot bg-emerald-500" />
            SIP trunk healthy
          </div>
          <p className="mt-2 text-xs leading-5 text-gray-500">
            5 campaigns active. 18 agents standing by for live transfers.
          </p>
        </div>
      </aside>
    </>
  );
}
