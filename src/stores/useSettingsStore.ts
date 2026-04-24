import { create } from "zustand";

interface SettingsState {
  isOpen: boolean;
  activeTab: "services" | "network" | "users" | "storage";
  platformOverride: string;

  open: () => void;
  close: () => void;
  toggle: () => void;
  setActiveTab: (tab: SettingsState["activeTab"]) => void;
  setPlatformOverride: (platform: string) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  isOpen: false,
  activeTab: "services",
  platformOverride: "",

  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setPlatformOverride: (platform) => set({ platformOverride: platform }),
}));
