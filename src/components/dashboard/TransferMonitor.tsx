import { useDashboardStore } from "@/stores/useDashboardStore";
import Icon from "@/components/ui/Icon";

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatEta(seconds: number): string {
  if (seconds <= 0) return "Done";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${Math.floor(seconds)}s`;
}

export default function TransferMonitor() {
  const transfers = useDashboardStore((s) => s.transfers);

  return (
    <section>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold tracking-tight text-on-surface">
          Active Transfers
        </h2>
        {transfers.length > 0 && (
          <span className="text-xs font-bold text-primary bg-primary-container px-3 py-1 rounded-full uppercase tracking-widest">
            {transfers.length} Active
          </span>
        )}
      </div>

      {transfers.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 bg-surface-container-low rounded-xl text-on-surface-variant">
          <Icon name="download" className="text-3xl mb-3 text-outline" />
          <p className="text-sm">No active downloads.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {transfers.map((transfer) => {
            const percent =
              transfer.size > 0
                ? Math.min(100, Math.round((1 - transfer.eta / 3600) * 100))
                : 0;
            return (
              <div
                key={transfer.id}
                className="p-4 bg-surface-container-lowest rounded-xl hover:bg-surface-container-low transition-all"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon name="download" className="text-lg text-primary shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-on-surface truncate">
                        {transfer.title}
                      </p>
                      <p className="text-[11px] text-on-surface-variant uppercase tracking-wider">
                        {transfer.source} • {transfer.protocol.toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-on-surface-variant shrink-0">
                    {formatBytes(transfer.size)} • ETA {formatEta(transfer.eta)}
                  </span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="h-1.5 flex-1 bg-surface-container-high rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                  <span className="text-xs font-bold text-primary shrink-0">
                    {transfer.downloadSpeed > 0
                      ? `${(transfer.downloadSpeed / 1024).toFixed(1)} KB/s`
                      : "Paused"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
