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
  /** Pulls live data from connected services via the proxy and populates the store. */
  loadFromApi: () => Promise<void>;
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

  loadFromApi: async () => {
    const json = async <T>(res: Response): Promise<T | null> =>
      res.ok ? ((await res.json()) as T) : null;

    const [radarr, sonarr, qbit, seerr] = await Promise.all([
      fetch("/api/proxy/radarr/api/v1/movie?pageSize=8&sortProp=added&sortDir=desc")
        .then((r) => json<Record<string, unknown>[]>(r))
        .catch(() => null),
      fetch("/api/proxy/sonarr/api/v3/series?pageSize=8&sortProp=added&sortDir=desc")
        .then((r) => json<Record<string, unknown>[]>(r))
        .catch(() => null),
      fetch("/api/proxy/qbittorrent/api/v2/torrents/info?filter=active")
        .then((r) => json<Record<string, unknown>[]>(r))
        .catch(() => null),
      fetch("/api/proxy/jellyseerr/api/v1/request")
        .then((r) => json<Record<string, unknown>[]>(r))
        .catch(() => null),
    ]);

    const { sonarrSeriesToMedia, radarrMovieToMedia, qbittorrentToTransfers, jellyseerrToRequests } =
      await import("@/lib/mappers");

    const movies = radarrMovieToMedia(radarr ?? []);
    const series = sonarrSeriesToMedia(sonarr ?? []);
    const allMedia = [...movies, ...series];

    set({
      heroMedia: allMedia[0] ?? null,
      recentlyAdded: allMedia.slice(0, 4),
      upcomingContent: allMedia.filter((m) => m.airDate).slice(0, 4),
      transfers: qbittorrentToTransfers(qbit ?? []),
      requests: jellyseerrToRequests(seerr ?? []),
    });
  },
}));
