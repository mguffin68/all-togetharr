"use client";

import TopNav from "@/components/layout/TopNav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <TopNav />
      <div className="flex h-[calc(100vh-72px)] overflow-hidden pt-[72px]">
        {children}
      </div>
    </div>
  );
}
