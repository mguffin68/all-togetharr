import SystemMetrics from "@/components/dashboard/widgets/SystemMetrics";
import RecentRequests from "@/components/dashboard/widgets/RecentRequests";

export default function RightRail() {
  return (
    <aside className="w-[320px] fixed right-0 top-[72px] h-[calc(100vh-72px)] bg-white/80 backdrop-blur-[20px] px-6 overflow-y-auto space-y-8"
      style={{ scrollbarWidth: "thin" }}
    >
      <SystemMetrics />
      <RecentRequests />
    </aside>
  );
}
