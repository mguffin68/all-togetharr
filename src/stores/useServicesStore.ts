import { create } from "zustand";

export type ServiceStatus = "online" | "offline" | "error" | "unknown";

export interface Service {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  status: ServiceStatus;
}

interface ServicesState {
  services: Service[];
  getService: (id: string) => Service | undefined;
  getServiceByName: (name: string) => Service | undefined;
  addService: (service: Omit<Service, "id">) => void;
  updateService: (id: string, updates: Partial<Service>) => void;
  toggleService: (id: string) => void;
  removeService: (id: string) => void;
  updateHealthStatus: (id: string, status: ServiceStatus) => void;
}

export const useServicesStore = create<ServicesState>((set) => ({
  services: [],

  getService: (id) =>
    useServicesStore.getState().services.find((s) => s.id === id),

  getServiceByName: (name) =>
    useServicesStore.getState().services.find((s) => s.name === name),

  addService: (service) => {
    const newService = { ...service, id: `svc_${Math.random().toString(36).substring(2, 11)}` };
    set((state) => ({ services: [...state.services, newService] }));
  },

  updateService: (id, updates) => {
    set((state) => ({
      services: state.services.map((s) => (s.id === id ? { ...s, ...updates } : s)),
    }));
  },

  toggleService: (id) => {
    set((state) => ({
      services: state.services.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s)),
    }));
  },

  removeService: (id) => {
    set((state) => ({ services: state.services.filter((s) => s.id !== id) }));
  },

  updateHealthStatus: (id, status) => {
    set((state) => ({
      services: state.services.map((s) => (s.id === id ? { ...s, status } : s)),
    }));
  },
}));
