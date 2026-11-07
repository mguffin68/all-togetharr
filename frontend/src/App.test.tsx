import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { THEME_STORAGE_KEY } from "./theme";

function stubColorScheme(prefersDark: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: query === "(prefers-color-scheme: dark)" ? prefersDark : false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

function stubHealth(response: Response | Error) {
  const fetchMock = vi.fn(() =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function healthy() {
  return new Response(JSON.stringify({ status: "ok", version: "1.2.3" }), { status: 200 });
}

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

function currentTheme() {
  return document.documentElement.dataset.theme;
}

beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  stubColorScheme(false);
  stubHealth(healthy());
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("app shell", () => {
  it("renders the name and the main landmark", () => {
    renderApp();

    expect(screen.getByRole("heading", { level: 1, name: "All-Togetharr" })).toBeTruthy();
    expect(screen.getByRole("main")).toBeTruthy();
  });

  it("shows the API version from the health check", async () => {
    const fetchMock = stubHealth(healthy());

    renderApp();

    expect(await screen.findByText("API 1.2.3")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith("/api/health", expect.anything());
  });

  it("shows when the API is offline after a network failure", async () => {
    stubHealth(new Error("connection refused"));

    renderApp();

    expect(await screen.findByText("API offline")).toBeTruthy();
  });

  it("shows when the API is offline after a bad status", async () => {
    stubHealth(new Response("{}", { status: 503 }));

    renderApp();

    expect(await screen.findByText("API offline")).toBeTruthy();
  });
});

describe("themes", () => {
  it("renders the light theme when the system prefers light", () => {
    renderApp();

    expect(currentTheme()).toBe("light");
    expect(screen.getByRole("button", { name: "Switch to dark theme" })).toBeTruthy();
  });

  it("renders the dark theme when the system prefers dark", () => {
    stubColorScheme(true);

    renderApp();

    expect(currentTheme()).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to light theme" })).toBeTruthy();
  });

  it("switches theme and remembers the choice", async () => {
    renderApp();

    await userEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));

    expect(currentTheme()).toBe("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to light theme" })).toBeTruthy();
  });

  it("prefers a saved theme over the system preference", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "light");
    stubColorScheme(true);

    renderApp();

    expect(currentTheme()).toBe("light");
  });

  it("ignores an invalid saved theme", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "purple");
    stubColorScheme(true);

    renderApp();

    expect(currentTheme()).toBe("dark");
  });

  it("still works when browser storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    renderApp();
    await userEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));

    expect(currentTheme()).toBe("dark");
  });
});
