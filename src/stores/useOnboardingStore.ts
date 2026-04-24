import { create } from "zustand";

export type OnboardingStep = "services" | "configure" | "test";

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
}

interface OnboardingState {
  currentStep: OnboardingStep;
  selectedServices: SelectedService[];
  currentServiceId: string | null;
  completed: boolean;

  goToStep: (step: OnboardingStep) => void;
  selectService: (service: SelectedService) => void;
  deselectService: (name: string) => void;
  setCurrentServiceId: (id: string | null) => void;
  updateServiceConfig: (name: string, config: Partial<SelectedService>) => void;
  markCompleted: () => void;
  reset: () => void;
  isSelected: (name: string) => boolean;
}

const serviceMap: Record<string, { icon: string; type: string }> = {
  Sonarr: { icon: "tv", type: "arr" },
  Radarr: { icon: "movie", type: "arr" },
  Prowlarr: { icon: "search", type: "indexer" },
  Jellyseerr: { icon: "list_alt", type: "request-manager" },
  Jellyfin: { icon: "stream", type: "media-server" },
  Plex: { icon: "album", type: "media-server" },
  Emby: { icon: "cloud", type: "media-server" },
  qBittorrent: { icon: "download", type: "download-client" },
  Transmission: { icon: "transfer_within_a_station", type: "download-client" },
};

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  currentStep: "services",
  selectedServices: [],
  currentServiceId: null,
  completed: false,

  goToStep: (step) => set({ currentStep: step }),

  selectService: (newService) => {
    const existing =
      serviceMap[newService.name];
    const service: SelectedService = {
      ...newService,
      ...(existing
        ? { type: existing.type, icon: existing.icon }
        : { type: newService.type, icon: newService.icon }),
    };
    set((state) => {
      const exists = state.selectedServices.findIndex(
        (s) => s.name === service.name
      );
      if (exists >= 0) {
        const updated = [...state.selectedServices];
        updated[exists] = service;
        return { selectedServices: updated };
      }
      return { selectedServices: [...state.selectedServices, service] };
    });
  },

  deselectService: (name) => {
    set((state) => ({
      selectedServices: state.selectedServices.filter((s) => s.name !== name),
    }));
  },

  setCurrentServiceId: (id) => set({ currentServiceId: id }),

  updateServiceConfig: (name, config) => {
    set((state) => ({
      selectedServices: state.selectedServices.map((s) =>
        s.name === name ? { ...s, ...config } : s
      ),
    }));
  },

  markCompleted: () => set({ completed: true }),

  reset: () =>
    set({
      currentStep: "services",
      selectedServices: [],
      currentServiceId: null,
      completed: false,
    }),

  isSelected: (name) => get().selectedServices.some((s) => s.name === name),
}));
