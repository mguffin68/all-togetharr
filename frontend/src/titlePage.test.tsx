import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { type Handler, fakeApi, healthy, json } from "./test/fakeApi";

const alice = { id: 1, name: "alice", role: "admin", auth_source: "local" };

function episode(season: number, number: number, extra: Record<string, unknown> = {}) {
  return {
    id: season * 100 + number,
    season_number: season,
    episode_number: number,
    name: `Episode name ${season}x${number}`,
    absolute_no: null,
    air_date: "2022-02-18",
    monitored: true,
    file_id: null,
    ...extra,
  };
}

const severance = {
  id: 7,
  type: "series",
  tmdb_id: 95396,
  tvdb_id: 371980,
  imdb_id: "tt11280740",
  name: "Severance",
  year: 2022,
  overview: "Mark leads a team of office workers.",
  poster_path: "/sev.jpg",
  status: "downloading",
  monitored: true,
  tags: ["drama"],
  added_at: "2026-01-01T00:00:00Z",
  seasons: [
    {
      id: 1,
      season_number: 0,
      monitored: false,
      episodes: [episode(0, 1, { name: "Behind the scenes" })],
    },
    {
      id: 2,
      season_number: 1,
      monitored: true,
      episodes: [
        episode(1, 1, { name: "Good News About Hell", file_id: 55 }),
        episode(1, 2, { name: null, air_date: null }),
      ],
    },
  ],
};

const arrival = {
  ...severance,
  id: 8,
  type: "movie",
  name: "Arrival",
  year: 2016,
  overview: "A linguist works with the military.",
  poster_path: null,
  status: "available",
  tags: [],
  seasons: [],
};

function titleApi(detail: Handler) {
  return fakeApi({
    "GET /api/health": healthy(),
    "GET /api/v1/auth/setup": () => json({ required: false }),
    "GET /api/v1/auth/me": () => json(alice),
    "GET /api/v1/titles/7": detail,
    "GET /api/v1/titles/8": () => json(arrival),
    "GET /api/v1/titles": () => json({ items: [], total: 0, page: 1, page_size: 50 }),
  });
}

function renderAt(url: string) {
  window.history.replaceState(null, "", url);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  );
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

describe("title page", () => {
  it("shows the title's metadata", async () => {
    titleApi(() => json(severance));

    renderAt("/titles/7");

    expect(await screen.findByRole("heading", { level: 2, name: "Severance" })).toBeTruthy();
    expect(screen.getByText("2022")).toBeTruthy();
    expect(screen.getByText("Series")).toBeTruthy();
    expect(screen.getByText("Downloading")).toBeTruthy();
    expect(screen.getByText("Mark leads a team of office workers.")).toBeTruthy();
    expect(screen.getByText("drama")).toBeTruthy();
    const poster = screen.getByRole("img", { name: "Poster for Severance" });
    expect(poster.getAttribute("src")).toContain("/sev.jpg");
  });

  it("links back to the library", async () => {
    titleApi(() => json(severance));

    renderAt("/titles/7");

    const back = await screen.findByRole("link", { name: "Back to library" });
    expect(back.getAttribute("href")).toBe("/");
  });

  it("lists seasons with their episodes", async () => {
    titleApi(() => json(severance));

    renderAt("/titles/7");

    const season1 = await screen.findByRole("region", { name: "Season 1" });
    expect(within(season1).getByText(/Good News About Hell/)).toBeTruthy();
    expect(within(season1).getByText(/Episode 2/)).toBeTruthy();
    expect(within(season1).getByText("Downloaded")).toBeTruthy();
    expect(within(season1).getByText("Missing")).toBeTruthy();

    const specials = screen.getByRole("region", { name: "Specials" });
    expect(within(specials).getByText(/Behind the scenes/)).toBeTruthy();
  });

  it("shows no seasons for a movie", async () => {
    titleApi(() => json(severance));

    renderAt("/titles/8");

    expect(await screen.findByRole("heading", { level: 2, name: "Arrival" })).toBeTruthy();
    expect(screen.getByText("Movie")).toBeTruthy();
    expect(screen.queryByRole("region", { name: /Season/ })).toBeNull();
    expect(screen.queryByRole("img", { name: /Poster/ })).toBeNull();
  });

  it("says when the title doesn't exist", async () => {
    titleApi(() => json({ detail: "Title not found" }, 404));

    renderAt("/titles/7");

    expect(await screen.findByText("Title not found.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Back to library" })).toBeTruthy();
  });

  it("treats a non-numeric id as not found without calling the API", async () => {
    const { calls } = titleApi(() => json(severance));

    renderAt("/titles/abc");

    expect(await screen.findByText("Title not found.")).toBeTruthy();
    expect(calls.some((c) => c.path.startsWith("/api/v1/titles/"))).toBe(false);
  });

  it("shows an error when the title can't load", async () => {
    titleApi(() => json({ detail: "boom" }, 500));

    renderAt("/titles/7");

    expect((await screen.findByRole("alert")).textContent).toContain("Couldn't load this title.");
  });
});
