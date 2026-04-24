import { create } from "zustand";

export interface MediaItem {
  id: string;
  title: string;
  type: "movie" | "series" | "episode";
  poster: string;
  mediaInfo: string;
  overrideQuality?: string;
  monitored?: boolean;
  seasonNumber?: number;
  episodeNumber?: number;
  airDate?: string;
  addedDate?: string;
  seriesId?: string;
}

export interface TransferItem {
  id: string;
  title: string;
  size: number;
  eta: number;
  downloadSpeed: number;
  output: string;
  outputPathExists: boolean;
  source: string;
  protocol: "nfs" | "smb" | "http";
  tracker?: string;
  magnet?: string;
}

export interface RequestItem {
  id: string;
  mediaId: number;
  requestType: "movie" | "series";
  status: "pending" | "approved" | "processing" | "downloaded";
  requestedBy: string;
  media: {
    title: string;
    year?: number;
    posterPath?: string;
  };
}

interface DashboardState {
  heroMedia: MediaItem | null;
  recentlyAdded: MediaItem[];
  upcomingContent: MediaItem[];
  transfers: TransferItem[];
  requests: RequestItem[];
  setHeroMedia: (item: MediaItem) => void;
  setRecentlyAdded: (items: MediaItem[]) => void;
  setUpcomingContent: (items: MediaItem[]) => void;
  setTransfers: (items: TransferItem[]) => void;
  setRequests: (items: RequestItem[]) => void;
  updateTransferStatus: (id: string, updates: Partial<TransferItem>) => void;
  updateRequestStatus: (id: string, status: RequestItem["status"]) => void;
  removeRequest: (id: string) => void;
  addRequest: (request: RequestItem) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  heroMedia: null,
  recentlyAdded: [],
  upcomingContent: [],
  transfers: [],
  requests: [],

  setHeroMedia: (item) => set({ heroMedia: item }),
  setRecentlyAdded: (items) => set({ recentlyAdded: items }),
  setUpcomingContent: (items) => set({ upcomingContent: items }),
  setTransfers: (items) => set({ transfers: items }),
  setRequests: (items) => set({ requests: items }),

  updateTransferStatus: (id, updates) => {
    set((state) => ({
      transfers: state.transfers.map((t) => (t.id === id ? { ...t, ...updates } : t)),
    }));
  },

  updateRequestStatus: (id, status) => {
    set((state) => ({
      requests: state.requests.map((r) => (r.id === id ? { ...r, status } : r)),
    }));
  },

  removeRequest: (id) => {
    set((state) => ({ requests: state.requests.filter((r) => r.id !== id) }));
  },

  addRequest: (request) => {
    set((state) => ({ requests: [...state.requests, request] }));
  },
}));
