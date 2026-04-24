import TopNav from "@/components/layout/TopNav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <TopNav />
      <div className="flex">
        <aside className="w-64 bg-surface-container-low/50 min-h-[calc(100vh-72px)] fixed left-0 top-[72px] flex flex-col p-4 space-y-6">
          {children}
        </aside>
      </div>
    </div>
  );
}
