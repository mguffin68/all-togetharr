import { useSettingsStore } from "@/stores/useSettingsStore";
import Icon from "@/components/ui/Icon";
import { Search } from "lucide-react";

export default function TopNav() {
  return (
    <header className="w-full sticky top-0 z-40 bg-[#F9F9FB] flex justify-between items-center px-6 py-4">
      <div className="flex items-center gap-8">
        <span className="text-xl font-bold tracking-[-0.02em] text-[#1D1D1F]">
          All Togetharr
        </span>
        <nav className="hidden md:flex space-x-6">
          <a href="/dashboard" className="text-[#1D1D1F] font-semibold font-['Inter'] tracking-tight">
            Dashboard
          </a>
          <a href="/dashboard" className="text-[#6E6E73] font-['Inter'] tracking-tight hover:bg-[#F2F4F6] transition-colors rounded-lg px-3 py-1">
            Library
          </a>
          <a href="/dashboard" className="text-[#6E6E73] font-['Inter'] tracking-tight hover:bg-[#F2F4F6] transition-colors rounded-lg px-3 py-1">
            Activity
          </a>
        </nav>
      </div>
      <div className="flex items-center space-x-4">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-outline-variant" />
          <input
            className="bg-surface-container-low border-none rounded-full py-2 pl-9 pr-4 text-sm w-64 focus:ring-1 focus:ring-primary outline-none transition-all"
            placeholder="Search media..."
            type="text"
          />
        </div>
        <button className="p-2 text-[#5F5E60] hover:bg-[#F2F4F6] rounded-full transition-colors">
          <Icon name="notifications" size={18} />
        </button>
        <button
          onClick={() => useSettingsStore.getState().toggle()}
          className="p-2 text-[#5F5E60] hover:bg-[#F2F4F6] rounded-full transition-colors"
        >
          <Icon name="settings" size={18} />
        </button>
      </div>
    </header>
  );
}
