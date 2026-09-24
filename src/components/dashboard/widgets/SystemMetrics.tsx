import { useProxyStore } from "@/stores/useProxyStore";
import Icon from "@/components/ui/Icon";

function formatSpeed(megabytesPerSec: number): string {
  if (megabytesPerSec >= 1) return `${megabytesPerSec.toFixed(1)} MB/s`;
  return `${(megabytesPerSec * 1024).toFixed(0)} KB/s`;
}

export default function SystemMetrics() {
  const metrics = useProxyStore((s) => s.systemMetrics);

  const downloadPct = Math.min(100, Math.round((metrics.downloadSpeed / 20) * 100));
  const diskPct = metrics.diskPercent;

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-bold tracking-tight text-on-surface">System Status</h3>
        <Icon name="analytics" className="text-outline" size={18} />
      </div>

      <div className="bg-surface-container-low p-5 rounded-xl space-y-6">
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-bold text-on-surface-variant uppercase tracking-widest">
            <span>Down Speed</span>
            <span className="text-primary">{formatSpeed(metrics.downloadSpeed)}</span>
          </div>
          <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-dim rounded-full transition-all"
              style={{ width: `${downloadPct}%` }}
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-xs font-bold text-on-surface-variant uppercase tracking-widest">
            <span>Storage ({Math.round(metrics.diskTotal / 1024)}TB)</span>
            <span className="text-primary">{diskPct}% Full</span>
          </div>
          <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                diskPct > 85 ? "bg-error" : "bg-primary-dim"
              }`}
              style={{ width: `${diskPct}%` }}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 pt-2">
          <div className="p-3 bg-surface rounded-lg">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase">CPU</p>
            <p className="text-lg font-black text-on-surface">{metrics.cpuUsage}%</p>
          </div>
          <div className="p-3 bg-surface rounded-lg">
            <p className="text-[10px] font-bold text-on-surface-variant uppercase">RAM</p>
            <p className="text-lg font-black text-on-surface">
              {metrics.memoryGb.toFixed(1)}GB
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
