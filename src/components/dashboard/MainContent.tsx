import HeroBanner, { MediaFeed } from "@/components/dashboard/MediaFeed";
import TransferMonitor from "@/components/dashboard/TransferMonitor";
import RequestQueue from "@/components/dashboard/RequestQueue";

export default function MainContent() {
  return (
    <div className="space-y-12" style={{ ml: "64px", mr: "320px", flex: 1, overflowY: "auto" }}>
      <HeroBanner />
      <MediaFeed />
      <TransferMonitor />
      <RequestQueue />
    </div>
  );
}
