import { HeroBanner, MediaFeed } from "@/components/dashboard/MediaFeed";
import TransferMonitor from "@/components/dashboard/TransferMonitor";
import RequestQueue from "@/components/dashboard/RequestQueue";

export default function MainContent() {
  return (
    <div className="space-y-12">
      <HeroBanner />
      <MediaFeed />
      <TransferMonitor />
      <RequestQueue />
    </div>
  );
}
