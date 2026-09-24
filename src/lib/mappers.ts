import type { MediaItem, TransferItem, RequestItem } from "@/stores/useDashboardStore";
import type { ServiceStatus } from "@/stores/useServicesStore";
import type { HealthSummary } from "@/stores/useProxyStore";

/**
 * Normalizes raw upstream API payloads (Sonarr, Radarr, qBittorrent,
 * Jellyseerr, …) into the dashboard store's client-side shapes.
 *
 * These are defensive: each service returns slightly different field names,
 * so every read is optional and falls back to a sensible default. Tweak the
 * property fallbacks per-service if your instance version differs.
 */

function str(value: unknown, fallback = ""): string {
  if (typeof value === "string" && value.length > 0) return value;
  if (typeof value === "number") return String(value);
  return fallback;
}
function num(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function sonarrSeriesToMedia(series: Record<string, unknown>[]): MediaItem[] {
  return series.map((s, i) => {
    const title = str(s.title, str(s.seriesName, `Series ${i + 1}`));
    const status = str(s.status, "monitoring");
    return {
      id: `sonarr-${str(s.id, String(i))}`,
      title,
      type: "series",
      poster: str(s.poster, ""),
      mediaInfo: str(s.network, ""),
      monitored: status !== "deleted",
      airDate: s.airDate ? new Date(str(s.airDate)).toISOString() : undefined,
    } satisfies MediaItem;
  });
}

export function radarrMovieToMedia(movies: Record<string, unknown>[]): MediaItem[] {
  return movies.map((m, i) => {
    const title = str(m.title, str(m.movieName, `Movie ${i + 1}`));
    return {
      id: `radarr-${str(m.id, String(i))}`,
      title,
      type: "movie",
      poster: str(m.poster, ""),
      mediaInfo: str(m.genres, "").replace(/,/g, " • "),
      overrideQuality: str(m.qualityProfileName),
      monitored: m.monitored !== false,
      airDate: m.inCinemas ? str(m.inCinemas) : undefined,
    } satisfies MediaItem;
  });
}

export function qbittorrentToTransfers(torrents: Record<string, unknown>[]): TransferItem[] {
  return torrents
    .filter((t) => (t.state as string) !== "error")
    .map((t, i) => {
      const progress = num(t.progress, 0); // 0..1
      const size = num(t.size, 0);
      const speed = num(t.dl_speed, 0); // bytes/s
      const remaining = speed > 0 ? (size * (1 - progress)) / speed : 0; // seconds
      return {
        id: str(t.hash, String(i)),
        title: str(t.name, `Torrent ${i + 1}`),
        size,
        eta: remaining,
        downloadSpeed: speed,
        output: str(t.save_path, ""),
        outputPathExists: t.save_path !== undefined,
        source: str(t.tracker, "qBittorrent"),
        protocol: "http",
        tracker: str(t.tracker),
      } satisfies TransferItem;
    });
}

export function jellyseerrToRequests(requests: Record<string, unknown>[]): RequestItem[] {
  return requests.map((r, i) => {
    const media = r.media as Record<string, unknown> | undefined;
    const user = r.user as Record<string, unknown> | undefined;
    const title = str(media?.title, str(r.title, `Request ${i + 1}`));
    const statusRaw = str(r.status, "pending");
    const status: RequestItem["status"] =
      statusRaw === "approved" || statusRaw === "approved_processing"
        ? "approved"
        : statusRaw === "processing"
          ? "processing"
          : statusRaw === "downloaded" || statusRaw === "completed"
            ? "downloaded"
            : "pending";
    return {
      id: str(r.id, String(i)),
      mediaId: num(r.id, i),
      requestType: str(r.type, "movie") === "series" ? "series" : "movie",
      status,
      requestedBy: str(user?.displayName, "Unknown"),
      media: {
        title,
        year: media?.year ? num(media.year) : undefined,
        posterPath: str(media?.poster, ""),
      },
    } satisfies RequestItem;
  });
}

export function healthItemToStatus(status: string): ServiceStatus {
  switch (status) {
    case "online":
    case "offline":
    case "error":
      return status;
    default:
      return "unknown";
  }
}

export function toHealthSummary(item: {
  name: string;
  status: string;
  icon?: string;
  url?: string;
}): HealthSummary {
  return {
    service: item.name,
    status: healthItemToStatus(item.status),
    icon: item.icon ?? "warning",
    url: item.url,
  };
}
