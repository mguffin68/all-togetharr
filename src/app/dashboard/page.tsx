import DashboardLayout from "./layout";
import LeftRail from "@/components/layout/LeftRail";
import MainContent from "@/components/dashboard/MainContent";
import RightRail from "@/components/layout/RightRail";
import SettingsOverlay from "@/components/settings/SettingsOverlay";
import { useSettingsStore } from "@/stores/useSettingsStore";
import { useEffect } from "react";

export default function DashboardPage() {
  const isOpen = useSettingsStore((s: unknown & { isOpen: boolean }) => s.isOpen);
  const close = useSettingsStore((s: unknown & { close: () => void }) => s.close);
  const toggle = useSettingsStore((s: unknown & { toggle: () => void }) => s.toggle);

  const [open, setOpen] = React.useState(false);
  const [closeFn, setCloseFn] = React.useState(() => () => {});
  const [toggleFn, setToggleFn] = React.useState(() => {});

  React.useEffect(() => {
    const store = useSettingsStore.getState();
    setOpen(store.isOpen);
    setCloseFn(store.close);
    setToggleFn(store.toggle);
  }, []);

  return (
    <DashboardLayout>
      <LeftRail onSettingsClick={open ? closeFn : toggleFn} />
      <main className="ml-64 mr-80 flex-1 overflow-y-auto p-8 space-y-12">
        <MainContent />
      </main>
      {open && <SettingsOverlay onClose={closeFn} />}
    </DashboardLayout>
  );
}
