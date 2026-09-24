import Image from "next/image";
import Icon from "@/components/ui/Icon";

export default function LeftRail() {
  return (
    <aside className="h-screen w-64 flex flex-col space-y-6">
      <div className="space-y-1">
        <p className="text-sm tracking-wide uppercase font-medium text-[#6E6E73] px-2 mb-4">
          Core Services
        </p>
        <div className="flex items-center justify-between px-3 py-2.5 text-[#1D1D1F] bg-white rounded-md shadow-sm">
          <div className="flex items-center space-x-3">
            <Icon name="dashboard" />
            <span className="font-medium">Dashboard</span>
          </div>
        </div>
        <div className="flex items-center justify-between px-3 py-2.5 text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-white/50 rounded-md cursor-pointer transition-all">
          <div className="flex items-center space-x-3">
            <Icon name="subscriptions" />
            <span className="font-medium">Library</span>
          </div>
        </div>
        <div className="flex items-center justify-between px-3 py-2.5 text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-white/50 rounded-md cursor-pointer transition-all">
          <div className="flex items-center space-x-3">
            <Icon name="download" />
            <span className="font-medium">Downloads</span>
          </div>
        </div>
        <div className="flex items-center justify-between px-3 py-2.5 text-[#6E6E73] hover:text-[#1D1D1F] hover:bg-white/50 rounded-md cursor-pointer transition-all">
          <div className="flex items-center space-x-3">
            <Icon name="pulse_alert" />
            <span className="font-medium">Activity</span>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-outline-variant/10">
        <p className="text-xs tracking-widest uppercase font-bold text-[#6E6E73] px-2 mb-4">
          Service Health
        </p>
        <div className="space-y-4 px-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-on-surface-variant">Plex Media</span>
            <div className="w-2 h-2 rounded-full bg-primary-fixed shadow-[0_0_8px_rgba(228,226,228,0.6)] pulse-soft"></div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-on-surface-variant">Radarr</span>
            <div className="w-2 h-2 rounded-full bg-primary-fixed shadow-[0_0_8px_rgba(228,226,228,0.6)] pulse-soft"></div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-on-surface-variant">Sonarr</span>
            <div className="w-2 h-2 rounded-full bg-error shadow-[0_0_8px_rgba(159,64,61,0.4)]"></div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-on-surface-variant">Transmission</span>
            <div className="w-2 h-2 rounded-full bg-primary-fixed shadow-[0_0_8px_rgba(228,226,228,0.6)] pulse-soft"></div>
          </div>
        </div>
      </div>

      <div className="mt-auto px-2 py-4 flex items-center space-x-3">
        <div className="w-8 h-8 rounded-full bg-surface-container-highest overflow-hidden relative">
          <Image
            src="https://api.dicebear.com/7.x/avataaars/svg?seed=admin"
            alt="Admin avatar"
            fill
            className="object-cover"
          />
        </div>
        <div>
          <p className="text-sm font-bold text-on-surface">Server Admin</p>
          <p className="text-[10px] text-primary tracking-wide">ONLINE</p>
        </div>
      </div>
    </aside>
  );
}
