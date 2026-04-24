export const SERVICE_TYPES = {
  ARR: "arr",
  MEDIA_SERVER: "media-server",
  DOWNLOAD_CLIENT: "download-client",
  INDEXER: "indexer",
} as const;

export const SERVICE_CATEGORIES = {
  SONARR: {
    name: "Sonarr",
    type: SERVICE_TYPES.ARR,
    icon: "tv",
    description: "TV Management",
    defaultPort: 8989,
    apiPaths: ["/api/v3/series"],
    healthPath: "/api/v3/health",
  } as const,
  RADARR: {
    name: "Radarr",
    type: SERVICE_TYPES.ARR,
    icon: "movie",
    description: "Movie Manager",
    defaultPort: 7878,
    apiPaths: ["/api/v1/movie"],
    healthPath: "/api/v1/health",
  } as const,
  PROWLARR: {
    name: "Prowlarr",
    type: SERVICE_TYPES.INDEXER,
    icon: "search",
    description: "Indexers",
    defaultPort: 9696,
    apiPaths: ["/api/v1/indexer"],
    healthPath: "/api/v1/status",
  } as const,
  JELLYSEERR: {
    name: "Jellyseerr",
    type: "request-manager",
    icon: "list_alt",
    description: "Requests",
    defaultPort: 5055,
    apiPaths: ["/api/v1/request"],
    healthPath: "/api/v1/status",
  } as const,
  JELLYFIN: {
    name: "Jellyfin",
    type: SERVICE_TYPES.MEDIA_SERVER,
    icon: "stream",
    description: "Open Server",
    defaultPort: 8096,
    apiPaths: ["/sys/config"],
    healthPath: "/health",
  } as const,
  PLEX: {
    name: "Plex",
    type: SERVICE_TYPES.MEDIA_SERVER,
    icon: "album",
    description: "Media Server",
    defaultPort: 32400,
    apiPaths: ["/library/sections"],
    authHeader: "X-Plex-Token",
    healthPath: "/scan",
  } as const,
  EMBY: {
    name: "Emby",
    type: SERVICE_TYPES.MEDIA_SERVER,
    icon: "cloud",
    description: "Library Sync",
    defaultPort: 8096,
    apiPaths: ["/System/Info/Public"],
    healthPath: "/System/Info/Public",
  } as const,
  QBITTORRENT: {
    name: "qBittorrent",
    type: SERVICE_TYPES.DOWNLOAD_CLIENT,
    icon: "download",
    description: "Download Client",
    defaultPort: 8080,
    apiPaths: ["/api/v2/torrents"],
    healthPath: null,
  } as const,
  TRANSMISSION: {
    name: "Transmission",
    type: SERVICE_TYPES.DOWNLOAD_CLIENT,
    icon: "transfer_within_a_station",
    description: "Download Manager",
    defaultPort: 9091,
    apiPaths: ["/transmission/rpc"],
    healthPath: "/transmission/rpc",
  } as const,
} as const;

export const SERVICE_OPTIONS = Object.values(SERVICE_CATEGORIES);

export type ServiceCategory = (typeof SERVICE_CATEGORIES)[keyof typeof SERVICE_CATEGORIES];
export type ServiceOption = (typeof SERVICE_OPTIONS)[number];
export type ServiceType = (typeof SERVICE_TYPES)[typeof SERVICE_TYPES[keyof typeof SERVICE_TYPES]];

export const HEALTH_STATUS = {
  ONLINE: "online",
  OFFLINE: "offline",
  ERROR: "error",
  UNKNOWN: "unknown",
} as const;
