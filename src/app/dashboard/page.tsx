"use client";

import { useEffect } from "react";
import DashboardLayout from "./layout";
import LeftRail from "@/components/layout/LeftRail";
import MainContent from "@/components/dashboard/MainContent";
import RightRail from "@/components/layout/RightRail";
import SettingsOverlay from "@/components/settings/SettingsOverlay";
import { useSettingsStore } from "@/stores/useSettingsStore";
import { useServicesStore } from "@/stores/useServicesStore";
import { useProxyStore } from "@/stores/useProxyStore";
import { useDashboardStore } from "@/stores/useDashboardStore";
import { toHealthSummary } from "@/lib/mappers";

// This page is a client component that loads data on mount; opt out of static
// prerendering so Next renders it dynamically instead of serializing handlers.
export const dynamic = "force-dynamic";

function useLoadDashboardData() {
  const addService = useServicesStore((s) => s.addService);
  const updateHealthStatus = useServicesStore((s) => s.updateHealthStatus);
  const updateHealthSummary = useProxyStore((s) => s.updateHealthSummary);
  const loadFromApi = useDashboardStore((s) => s.loadFromApi);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      // 1. Known services → client store (drives settings overlay + health rail)
      const servicesRes = await fetch("/api/services").catch(() => null);
      if (servicesRes?.ok) {
        const list = await servicesRes.json();
        if (!cancelled && Array.isArray(list)) {
          list.forEach(
            (svc: { id: string; name: string; type: string; enabled: boolean }) =>
              addService({ ...svc, status: "unknown" })
          );
        }
      }

      // 2. Live health → proxy store (drives system metrics / health rail)
      const healthRes = await fetch("/api/health").catch(() => null);
      if (healthRes?.ok) {
        const data = await healthRes.json();
        const items = (data.services ?? []).map(toHealthSummary);
        if (!cancelled) {
          updateHealthSummary(items);
          items.forEach((h: ReturnType<typeof toHealthSummary>) =>
            updateHealthStatus(h.service, h.status)
          );
        }
      }

      // 3. Dashboard content (media, transfers, requests) via the raw proxy
      if (!cancelled) await loadFromApi();
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [addService, updateHealthStatus, updateHealthSummary, loadFromApi]);
}

export default function DashboardPage() {
  const isOpen = useSettingsStore((s) => s.isOpen);
  const close = useSettingsStore((s) => s.close);
  const toggle = useSettingsStore((s) => s.toggle);

  useLoadDashboardData();

  // Close the settings overlay with the Escape key.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, close]);

  return (
    <DashboardLayout>
      <LeftRail />
      <main className="ml-64 mr-80 flex-1 overflow-y-auto p-8">
        <MainContent />
      </main>
      <RightRail />
      {isOpen && <SettingsOverlay onClose={close} />}
    </DashboardLayout>
  );
}
