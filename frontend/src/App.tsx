import React from "react";
import { useHealth } from "./health";
import { useTheme } from "./theme";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { data, isLoading, error } = useHealth();

  let apiStatus: React.ReactNode;
  if (isLoading) {
    apiStatus = null;
  } else if (error || !data) {
    apiStatus = "API offline";
  } else {
    apiStatus = `API ${data.version}`;
  }

  const btnLabel = theme === "light" ? "Switch to dark theme" : "Switch to light theme";

  return (
    <div className="min-h-screen">
      <header className="p-4">
        <h1 className="text-2xl font-bold">All-Togetharr</h1>
        {apiStatus && <p className="text-sm mt-1">{apiStatus}</p>}
        <button onClick={toggleTheme} className="mt-2 px-3 py-1 rounded">
          {btnLabel}
        </button>
      </header>
      <main className="p-4">
        <p className="text-sm">Coming soon — your personal media hub.</p>
      </main>
    </div>
  );
}
