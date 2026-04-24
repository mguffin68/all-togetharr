import { create } from "zustand";

export interface HealthSummary {
  service: string;
  status: "online" | "offline" | "error" | "unknown";
  icon: string;
  url?: string;
}

export interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  memoryGb: number;
  bandwidth: number;
  diskUsed: number;
  diskTotal: number;
  diskPercent: number;
  downloadSpeed: number;
}

interface ProxyState {
  selectedServices: SelectedService[];
  healthSummary: HealthSummary[];
  systemMetrics: SystemMetrics;

  updateMetrics: (metrics: Partial<SystemMetrics>) => void;
  updateHealthSummary: (items: HealthSummary[]) => void;
  addHealthSummary: (item: HealthSummary) => void;
  updateHealthStatus: (service: string, status: HealthSummary["status"]) => void;
  getHealthSummary: (service: string) => HealthSummary | undefined;
  getOnlineCount: () => number;
  getErrorCount: () => number;
  getOfflineCount: () => number;
}

export interface SelectedService {
  name: string;
  type: string;
  icon: string;
  description: string;
  baseUrl?: string;
  apiKey?: string;
  port?: number;
  categories?: string[];
  rootPath?: string;
  protocol?: string;
  enabled: boolean;
}

export const useProxyStore = create<ProxyState>((set, get) => ({
  selectedServices: [],
  healthSummary: [],
  systemMetrics: {
    cpuUsage: 0,
    memoryUsage: 0,
    memoryGb: 0,
    bandwidth: 0,
    diskUsed: 0,
    diskTotal: 12000,
    diskPercent: 0,
    downloadSpeed: 0,
  },

  updateMetrics: (metrics) =>
    set((state) => ({
      systemMetrics: { ...state.systemMetrics, ...metrics },
    })),

  updateHealthSummary: (items) => set({ healthSummary: items }),

  addHealthSummary: (item) => {
    set((state) => {
      const exists = state.healthSummary.findIndex((s) => s.service === item.service);
      if (exists >= 0) {
        const updated = [...state.healthSummary];
        updated[exists] = item;
        return { healthSummary: updated };
      }
      return { healthSummary: [...state.healthSummary, item] };
    });
  },

  updateHealthStatus: (service, status) => {
    set((state) => ({
      healthSummary: state.healthSummary.map((h) =>
        h.service === service ? { ...h, status } : h
      ),
    }));
  },

  getHealthSummary: (service) =>
    get().healthSummary.find((s) => s.service === service),

  getOnlineCount: () =>
    get().healthSummary.filter((s) => s.status === "online").length,

  getErrorCount: () =>
    get().healthSummary.filter((s) => s.status === "error").length,

  getOfflineCount: () =>
    get().healthSummary.filter((s) => s.status === "offline").length,
}));
