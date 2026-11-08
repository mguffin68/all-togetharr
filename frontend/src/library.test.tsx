import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { type FakeRequest, fakeApi, healthy, json } from "./test/fakeApi";

const alice = { id: 1, name: "alice", role: "admin", auth_source: "local" };

function title(id: number, name: string, extra: Record<string, unknown> = {}) {
  return {
    id,
    type: "movie",
    tmdb_id: 1000 + id,
    tvdb_id: null,
    imdb_id: null,
    name,
    year: 2021,
    overview: null,
    poster_path: null,
    status: "available",
    monitored: true,
    tags: [],
    added_at: "2026-01-01T00:00:00Z",
    ...extra,
  };
}

type Page = { items: unknown[]; total: number };

/** Signed-in API whose title list is produced from the request's query string. */
function libraryApi(list: (search: URLSearchParams) => Page | Response) {
  const api = fakeApi({
    "GET /api/health": healthy(),
    "GET /api/v1/auth/setup": () => json({ required: false }),
    "GET /api/v1/auth/me": () => json(alice),
    "GET /api/v1/titles": (req: FakeRequest) => {
      const result = list(req.search);
      if (result instanceof Response) return result;
      return json({
        ...result,
        page: Number(req.search.get("page") ?? "1"),
        page_size: Number(req.search.get("page_size") ?? "50"),
      });
    },
  });
  const listCalls = () => api.calls.filter((c) => c.path === "/api/v1/titles");
  const lastList = () => {
    const all = listCalls();
    return all[all.length - 1]?.search;
  };
  return { ...api, listCalls, lastList };
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

function currentParams() {
  return new URLSearchParams(window.location.search);
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

describe("library list", () => {
  it("lists titles with their year and the total", async () => {
    const { lastList } = libraryApi(() => ({
      items: [title(1, "Arrival", { year: 2016 }), title(2, "Severance", { type: "series", year: 2022 })],
      total: 2,
    }));

    renderAt("/");

    expect(await screen.findByText("Arrival")).toBeTruthy();
    expect(screen.getByText("Severance")).toBeTruthy();
    expect(screen.getByText("2016")).toBeTruthy();
    expect(screen.getByText("2 titles")).toBeTruthy();
    expect(lastList()?.get("page")).toBe("1");
  });

  it("links each title to its page", async () => {
    libraryApi(() => ({ items: [title(7, "Arrival")], total: 1 }));

    renderAt("/");

    const link = await screen.findByRole("link", { name: /Arrival/ });
    expect(link.getAttribute("href")).toBe("/titles/7");
  });

  it("says when the library is empty", async () => {
    libraryApi(() => ({ items: [], total: 0 }));

    renderAt("/");

    expect(await screen.findByText("No titles yet.")).toBeTruthy();
  });

  it("says when no titles match the filters", async () => {
    libraryApi(() => ({ items: [], total: 0 }));

    renderAt("/?type=series");

    expect(await screen.findByText("No titles match these filters.")).toBeTruthy();
  });

  it("shows an error when the list can't load", async () => {
    libraryApi(() => json({ detail: "boom" }, 500));

    renderAt("/");

    expect((await screen.findByRole("alert")).textContent).toContain("Couldn't load the library.");
  });
});

describe("library filters", () => {
  it("filters by type and keeps it in the URL", async () => {
    const { lastList } = libraryApi(() => ({ items: [title(1, "Arrival")], total: 1 }));

    renderAt("/?page=2");
    await screen.findByText("Arrival");
    await userEvent.selectOptions(screen.getByLabelText("Type"), "movie");

    await waitFor(() => expect(lastList()?.get("type")).toBe("movie"));
    expect(lastList()?.get("page")).toBe("1");
    expect(currentParams().get("type")).toBe("movie");
    expect(currentParams().get("page")).toBeNull();
  });

  it("filters by status", async () => {
    const { lastList } = libraryApi(() => ({ items: [title(1, "Arrival")], total: 1 }));

    renderAt("/");
    await screen.findByText("Arrival");
    await userEvent.selectOptions(screen.getByLabelText("Status"), "downloading");

    await waitFor(() => expect(lastList()?.get("status")).toBe("downloading"));
    expect(currentParams().get("status")).toBe("downloading");
  });

  it("searches by name when the search is submitted", async () => {
    const { lastList } = libraryApi(() => ({ items: [title(1, "Arrival")], total: 1 }));

    renderAt("/");
    await screen.findByText("Arrival");
    await userEvent.type(screen.getByLabelText("Search"), "dune{Enter}");

    await waitFor(() => expect(lastList()?.get("q")).toBe("dune"));
    expect(currentParams().get("q")).toBe("dune");
  });

  it("restores filters and page from the URL", async () => {
    const { lastList } = libraryApi(() => ({ items: [title(1, "Severance")], total: 120 }));

    renderAt("/?type=series&status=available&q=sev&page=2");
    await screen.findByText("Severance");

    const params = lastList();
    expect(params?.get("type")).toBe("series");
    expect(params?.get("status")).toBe("available");
    expect(params?.get("q")).toBe("sev");
    expect(params?.get("page")).toBe("2");
    expect((screen.getByLabelText("Type") as HTMLSelectElement).value).toBe("series");
    expect((screen.getByLabelText("Status") as HTMLSelectElement).value).toBe("available");
    expect((screen.getByLabelText("Search") as HTMLInputElement).value).toBe("sev");
  });

  it("ignores unknown filter values in the URL", async () => {
    const { lastList } = libraryApi(() => ({ items: [title(1, "Arrival")], total: 1 }));

    renderAt("/?type=cartoon&status=lost&page=abc");
    await screen.findByText("Arrival");

    const params = lastList();
    expect(params?.has("type")).toBe(false);
    expect(params?.has("status")).toBe(false);
    expect(params?.get("page")).toBe("1");
  });
});

describe("library paging", () => {
  it("pages forward and back", async () => {
    const { lastList } = libraryApi((s) => ({
      items: [title(Number(s.get("page")), `Title on page ${s.get("page")}`)],
      total: 120,
    }));

    renderAt("/");
    await screen.findByText("Title on page 1");
    expect(screen.getByText("Page 1 of 3")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Previous page" }) as HTMLButtonElement).disabled).toBe(true);

    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Title on page 2")).toBeTruthy();
    expect(lastList()?.get("page")).toBe("2");
    expect(currentParams().get("page")).toBe("2");
    expect(screen.getByText("Page 2 of 3")).toBeTruthy();

    await userEvent.click(screen.getByRole("button", { name: "Previous page" }));
    expect(await screen.findByText("Title on page 1")).toBeTruthy();
  });

  it("disables next on the last page", async () => {
    libraryApi(() => ({ items: [title(1, "Last one")], total: 120 }));

    renderAt("/?page=3");
    await screen.findByText("Last one");

    expect(screen.getByText("Page 3 of 3")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Next page" }) as HTMLButtonElement).disabled).toBe(true);
  });
});
