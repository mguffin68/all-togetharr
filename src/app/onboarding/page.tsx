"use client";

import { useEffect } from "react";
import { redirect } from "next/navigation";
import TopNav from "@/components/layout/TopNav";
import ServiceSelection from "@/components/onboarding/steps/ServiceSelection";
import ConnectionSetup from "@/components/onboarding/steps/ConnectionSetup";
import { useOnboardingStore } from "@/stores/useOnboardingStore";

const STEP_LABELS: Record<string, string> = {
  services: "Step 1 of 3",
  configure: "Step 2 of 3",
  test: "Step 3 of 3",
};

export default function OnboardingPage() {
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const completed = useOnboardingStore((s) => s.completed);

  // Once the wizard is complete, hand off to the dashboard.
  useEffect(() => {
    if (completed) {
      const t = setTimeout(() => redirect("/dashboard"), 800);
      return () => clearTimeout(t);
    }
  }, [completed]);

  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <TopNav />
      <main className="flex-1 flex items-center justify-center p-6 md:p-12 min-h-[calc(100vh-72px)]">
        <div className="max-w-5xl w-full">
          {completed ? (
            <div className="flex flex-col items-center justify-center py-24 text-on-surface">
              <p className="text-2xl font-bold">Setup complete.</p>
              <p className="text-on-surface-variant mt-2">
                Redirecting to your dashboard…
              </p>
            </div>
          ) : currentStep === "services" ? (
            <ServiceSelection />
          ) : (
            <ConnectionSetup />
          )}
        </div>
      </main>

      <div className="fixed right-6 bottom-6 flex items-center gap-4">
        <div className="flex items-center gap-2 bg-surface-container-low px-4 py-2 rounded-full shadow-sm">
          <span className="w-2 h-2 rounded-full bg-primary-fixed animate-pulse" />
          <span className="text-[10px] uppercase tracking-[0.1em] font-bold text-on-surface-variant">
            {STEP_LABELS[currentStep]}
          </span>
        </div>
      </div>
    </div>
  );
}
