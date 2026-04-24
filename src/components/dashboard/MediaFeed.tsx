import { useDashboardStore } from "@/stores/useDashboardStore";
import Image from "next/image";

export function HeroBanner() {
  const heroMedia = useDashboardStore((s) => s.heroMedia);

  if (!heroMedia) {
    return (
      <section className="relative h-64 rounded-xl overflow-hidden bg-surface-container-low animate-pulse">
        <div className="absolute bottom-6 left-8 space-y-1" />
      </section>
    );
  }

  return (
    <section className="relative h-64 rounded-xl overflow-hidden group">
      <Image
        src={heroMedia.poster}
        alt={heroMedia.title}
        fill
        className="object-cover transition-transform duration-700 group-hover:scale-105"
        priority
      />
      <div className="absolute inset-0 bg-gradient-to-t from-inverse_surface from-50% via-transparent to-transparent" />
      <div className="absolute bottom-6 left-8 space-y-1">
        <span className="px-2 py-1 rounded text-[10px] text-on-primary font-bold tracking-widest uppercase bg-primary">
          Upcoming Release
        </span>
        <h1 className="text-3xl font-bold text-white tracking-tight">
          {heroMedia.title}
        </h1>
        <p className="text-white/70 text-sm">
          {heroMedia.type === "movie"
            ? "Streaming now • Directed by Unknown"
            : `Episode ${heroMedia.episodeNumber || "?"} • ${heroMedia.mediaInfo}`}
        </p>
      </div>
    </section>
  );
}

export function MediaFeed() {
  const recentlyAdded = useDashboardStore((s) => s.recentlyAdded);
  const upcomingContent = useDashboardStore((s) => s.upcomingContent);

  return (
    <div className="space-y-12">
      {/* Recently Added Bento Grid */}
      <section>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold tracking-tight text-on-surface">
            Recently Added
          </h2>
          <button className="text-sm text-primary font-medium hover:underline">
            View all
          </button>
        </div>
        {recentlyAdded.length > 0 ? (
          <div className="grid grid-cols-4 gap-6">
            {recentlyAdded.map((item, index) => (
              <div
                key={item.id}
                className={index === 0 ? "col-span-2 row-span-2 space-y-3" : "space-y-3"}
              >
                <div
                  className={
                    index === 0
                      ? "relative aspect-video rounded-xl overflow-hidden bg-surface-container-low group"
                      : "aspect-[2/3] rounded-xl overflow-hidden bg-surface-container-low group"
                  }
                >
                  <Image
                    src={item.poster}
                    alt={item.title}
                    fill
                    className="object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                  {index === 0 && (
                    <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <span className="material-symbols-outlined text-white text-5xl">
                        play_circle
                      </span>
                    </div>
                  )}
                </div>
                <div>
                  <h3
                    className={
                      index === 0
                        ? "font-bold text-on-surface"
                        : "text-sm font-bold text-on-surface"
                    }
                  >
                    {item.title}
                  </h3>
                  <p
                    className={
                      index === 0
                        ? "text-sm text-on-surface-variant"
                        : "text-[11px] text-on-surface-variant font-medium uppercase tracking-wider"
                    }
                  >
                    {item.type === "movie"
                      ? `Movie • ${item.overrideQuality || "1080P"}`
                      : `Series • S${item.seasonNumber || "?"} E${item.episodeNumber || "?"}`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-40 text-on-surface-variant text-sm">
            No recently added media.
          </div>
        )}
      </section>

      {/* Calendar */}
      <section>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold tracking-tight text-on-surface">
            Calendar
          </h2>
        </div>
        <div className="space-y-4">
          {upcomingContent.map((item) => (
            <div
              key={item.id}
              className="flex items-center p-4 bg-surface-container-lowest rounded-xl hover:bg-surface-container-low transition-all"
            >
              <div className="w-16 h-16 rounded-lg bg-surface-container-high flex flex-col items-center justify-center text-on-surface shrink-0">
                {item.airDate && (
                  <>
                    <span className="text-xs font-bold uppercase">
                      {new Date(item.airDate).toLocaleString("default", { month: "short" }).toUpperCase()}
                    </span>
                    <span className="text-xl font-black">
                      {new Date(item.airDate).getDate()}
                    </span>
                  </>
                )}
                {!item.airDate && (
                  <span className="text-lg font-bold">?</span>
                )}
              </div>
              <div className="ml-6 flex-1">
                <h4 className="font-bold text-on-surface">{item.title}</h4>
                <p className="text-sm text-on-surface-variant">
                  {item.type === "series" ? "Series Update" : "Movie Release"} •{" "}
                  {item.monitored ? "Radarr Tracking" : "Sonarr Tracking"}
                </p>
              </div>
              <div className="flex items-center space-x-2">
                <span className="material-symbols-outlined text-outline text-lg">
                  notifications_active
                </span>
                <span className="text-xs font-bold text-primary bg-primary-container rounded-full uppercase tracking-tighter">
                  Monitored
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
