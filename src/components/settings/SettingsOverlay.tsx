import { useSettingsStore } from "@/stores/useSettingsStore";

const SERVICE_LIST = [
  { name: "Plex Media Server", type: "internal-node", icon: "dns", port: 32400, enabled: true },
  { name: "Transmission VPN", type: "gateway", icon: "lan", port: 9091, enabled: true },
  { name: "Jellyseerr", type: "request-mgr", icon: "smart_toy", port: 5055, enabled: false },
  { name: "Sonarr", type: "series-mgr", icon: "tv", port: 8989, enabled: true },
  { name: "Radarr", type: "movie-mgr", icon: "movie", port: 7878, enabled: true },
];

export default function SettingsOverlay({ onClose }: { onClose: () => void }) {
  const activeTab = useSettingsStore((s) => s.activeTab);
  const setActiveTab = useSettingsStore((s) => s.setActiveTab);
  const toggleService = (name: string) => {
    const current = SERVICE_LIST.find((s) => s.name === name);
    if (current) {
      console.log(`Toggle ${current.name} (currently ${current.enabled ? "on" : "off"})`);
    }
  };

  const tabs = [
    { key: "services" as const, label: "Services" },
    { key: "network" as const, label: "Network" },
    { key: "users" as const, label: "Users" },
    { key: "storage" as const, label: "Storage" },
  ];

  const runningCount = SERVICE_LIST.filter((s) => s.enabled).length;

  return (
    <div
      className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 transition-opacity"
      onClick={onClose}
    >
      <aside className="fixed right-0 h-full w-96 shadow-2xl bg-white/80 backdrop-blur-xl flex flex-col p-8 slide-in-right">
        <div className="mb-10 flex justify-between items-start">
          <div>
            <h2 className="text-[#1D1D1F] font-bold text-2xl tracking-tight">
              Server Settings
            </h2>
            <p className="text-[#6E6E73] text-sm font-medium mt-1">
              Advanced Configuration
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-container rounded-full transition-all"
          >
            <span className="material-symbols-outlined text-on-surface">close</span>
          </button>
        </div>

        <nav className="flex border-b border-outline-variant/10 mb-8 overflow-x-auto no-scrollbar">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 border-b-2 transition-colors font-['Inter'] text-body-md whitespace-nowrap ${
                activeTab === tab.key
                  ? "border-[#5F5E60] text-[#1D1D1F]"
                  : "border-transparent text-[#6E6E73] hover:text-[#1D1D1F]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="flex-1 overflow-y-auto no-scrollbar">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-[10px] font-bold uppercase tracking-[0.2em] text-outline">
              Active Modules
            </h3>
            <span className="text-[10px] font-bold text-primary bg-primary-container px-2 py-0.5 rounded-full">
              {runningCount} Running
            </span>
          </div>

          <div className="space-y-3">
            {SERVICE_LIST.map((service) => (
              <div
                key={service.name}
                className="group flex items-center justify-between p-4 bg-surface-container-low/50 hover:bg-surface-container-low transition-all rounded-xl border border-transparent hover:border-outline-variant/10"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-primary shadow-sm">
                    <span
                      className="material-symbols-outlined"
                      style={{
                        fontVariationSettings: "FILL 1",
                      }}
                    >
                      {service.icon}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-on-surface">{service.name}</p>
                    <p className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider">
                      {service.type === "gateway"
                        ? "Gateway"
                        : service.type === "request-mgr"
                          ? "Request Mgr"
                          : "Internal Node"} • Port {service.port}
                    </p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    checked={service.enabled}
                    onChange={() => toggleService(service.name)}
                    className="sr-only peer"
                    type="checkbox"
                  />
                  <div className="w-9 h-5 bg-outline-variant/30 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary" />
                </label>
              </div>
            ))}

            <div className="pt-6">
              <button className="w-full group flex flex-col items-center justify-center p-8 border-2 border-dashed border-outline-variant/20 hover:border-primary/40 rounded-2xl transition-all hover:bg-white/50">
                <div className="w-12 h-12 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant group-hover:scale-110 transition-transform mb-3">
                  <span className="material-symbols-outlined text-2xl">add</span>
                </div>
                <span className="text-sm font-bold text-on-surface tracking-tight">
                  Add Service
                </span>
                <span className="text-[10px] text-on-surface-variant mt-1">
                  Connect new docker or API node
                </span>
              </button>
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-outline-variant/10">
          <button className="w-full py-4 bg-primary text-on-primary font-bold rounded-xl active:scale-[0.98] transition-all shadow-lg shadow-primary/20">
            Apply Configuration
          </button>
          <p className="text-center text-[10px] text-outline mt-4 font-medium uppercase tracking-[0.1em]">
            All Togetharr v2.4.1 (Stable Build)
          </p>
        </div>
      </aside>
    </div>
  );
}
