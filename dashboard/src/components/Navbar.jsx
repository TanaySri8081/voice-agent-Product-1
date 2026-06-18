import { Bell, ChevronDown, Menu, Search } from "lucide-react";
import { Button } from "./ui/Button";

export default function Navbar({ onMenuClick }) {
  return (
    <header className="sticky top-0 z-30 border-b border-gray-200/80 bg-white/80 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuClick}>
          <Menu className="h-5 w-5" />
        </Button>
        <div className="hidden min-w-0 flex-1 items-center gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500 md:flex">
          <Search className="h-4 w-4" />
          <span>Search calls, contacts, campaigns...</span>
        </div>
        <button className="ml-auto hidden items-center gap-2 rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm md:flex">
          North America Sales
          <ChevronDown className="h-4 w-4 text-gray-400" />
        </button>
        <Button variant="secondary" size="icon">
          <Bell className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white py-1 pl-1 pr-3 shadow-sm">
          <div className="grid h-8 w-8 place-items-center rounded-xl bg-gray-950 text-xs font-bold text-white">
            AR
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-semibold leading-4 text-gray-950">Anmol Raj</p>
            <p className="text-xs text-gray-500">Admin</p>
          </div>
        </div>
      </div>
    </header>
  );
}
