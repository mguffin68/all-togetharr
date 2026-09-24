import { useDashboardStore } from "@/stores/useDashboardStore";
import Icon from "@/components/ui/Icon";

const STATUS_STYLES: Record<
  string,
  { dot: string; text: string; label: string }
> = {
  pending: { dot: "bg-outline", text: "text-outline", label: "Pending" },
  approved: { dot: "bg-primary", text: "text-primary", label: "Approved" },
  processing: { dot: "bg-primary-fixed", text: "text-primary", label: "Processing" },
  downloaded: { dot: "bg-surface-container-highest", text: "text-on-surface-variant", label: "Downloaded" },
};

export default function RequestQueue() {
  const requests = useDashboardStore((s) => s.requests);
  const updateRequestStatus = useDashboardStore((s) => s.updateRequestStatus);

  return (
    <section>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold tracking-tight text-on-surface">
          Request Queue
        </h2>
        {requests.length > 0 && (
          <span className="text-xs font-bold text-primary bg-primary-container px-3 py-1 rounded-full uppercase tracking-widest">
            {requests.length} Total
          </span>
        )}
      </div>

      {requests.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-40 bg-surface-container-low rounded-xl text-on-surface-variant">
          <Icon name="list_alt" className="text-3xl mb-3 text-outline" />
          <p className="text-sm">No pending requests.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {requests.map((request) => {
            const status = STATUS_STYLES[request.status] ?? STATUS_STYLES.pending;
            return (
              <div
                key={request.id}
                className="flex items-center space-x-4 p-3 bg-surface-container-lowest rounded-xl hover:bg-surface-container-low transition-all"
              >
                <div className="w-12 h-16 rounded-md overflow-hidden bg-surface-container-low shrink-0 flex items-center justify-center">
                  <Icon name={request.requestType === "movie" ? "movie" : "tv"} className="text-outline" />
                </div>
                <div className="flex-1 overflow-hidden">
                  <p className="text-sm font-bold text-on-surface truncate">
                    {request.media.title}
                    {request.media.year ? ` (${request.media.year})` : ""}
                  </p>
                  <p className="text-[11px] text-on-surface-variant">
                    Requested by <span className="font-bold">{request.requestedBy}</span>
                  </p>
                  <div className="mt-1 flex items-center">
                    <span className={`w-1.5 h-1.5 rounded-full ${status.dot} mr-1.5`} />
                    <span className={`text-[10px] font-bold ${status.text} tracking-tighter uppercase`}>
                      {status.label}
                    </span>
                  </div>
                </div>
                {request.status === "pending" && (
                  <button
                    onClick={() => updateRequestStatus(request.id, "approved")}
                    className="shrink-0 text-[10px] font-bold text-on-surface uppercase tracking-widest bg-surface-container-high hover:bg-surface-container-highest px-3 py-2 rounded-full transition-colors"
                  >
                    Approve
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
