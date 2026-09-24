import { useDashboardStore } from "@/stores/useDashboardStore";
import Icon from "@/components/ui/Icon";

const STATUS_STYLES: Record<string, { dot: string; text: string; label: string }> = {
  pending: { dot: "bg-outline", text: "text-outline", label: "Pending" },
  approved: { dot: "bg-primary", text: "text-primary", label: "Approved" },
  processing: { dot: "bg-primary-fixed", text: "text-primary", label: "Processing" },
  downloaded: { dot: "bg-surface-container-highest", text: "text-on-surface-variant", label: "Downloaded" },
};

export default function RecentRequests() {
  const requests = useDashboardStore((s) => s.requests);
  const recent = requests.slice(0, 3);

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-bold tracking-tight text-on-surface">Recent Requests</h3>
        <Icon name="history" className="text-outline" size={18} />
      </div>

      {recent.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-24 bg-surface-container-low rounded-xl">
          <p className="text-xs text-on-surface-variant">No recent requests.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {recent.map((request) => {
            const status = STATUS_STYLES[request.status] ?? STATUS_STYLES.pending;
            return (
              <div
                key={request.id}
                className="flex items-center space-x-4 p-2 hover:bg-surface-container-low rounded-lg transition-colors"
              >
                <div className="w-12 h-16 rounded-md overflow-hidden bg-surface-container-low shrink-0 flex items-center justify-center">
                  <Icon
                    name={request.requestType === "movie" ? "movie" : "tv"}
                    className="text-outline"
                  />
                </div>
                <div className="flex-1 overflow-hidden">
                  <p className="text-sm font-bold text-on-surface truncate">
                    {request.media.title}
                  </p>
                  <p className="text-[10px] text-on-surface-variant">
                    Requested by <span className="font-bold">{request.requestedBy}</span>
                  </p>
                  <div className="mt-1 flex items-center">
                    <span className={`w-1.5 h-1.5 rounded-full ${status.dot} mr-1.5`} />
                    <span className={`text-[10px] font-bold ${status.text} tracking-tighter uppercase`}>
                      {status.label}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <button className="w-full py-3 bg-surface-container-high hover:bg-surface-container-highest transition-colors rounded-xl text-xs font-bold text-on-surface uppercase tracking-widest">
        Manage Requests
      </button>
    </section>
  );
}
