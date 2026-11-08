import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { type Handler, fakeApi, healthy, json, noContent, unauthorized } from "./test/fakeApi";

const alice = { id: 1, name: "alice", role: "admin", auth_source: "local" };

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

function api(routes: Record<string, Handler>) {
  return fakeApi({ "GET /api/health": healthy(), ...routes });
}

async function fillCredentials(name: string, password: string) {
  await userEvent.type(screen.getByLabelText("Name"), name);
  await userEvent.type(screen.getByLabelText("Password"), password);
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
});

describe("first-run setup", () => {
  it("shows the setup screen when no users exist", async () => {
    api({ "GET /api/v1/auth/setup": () => json({ required: true }) });

    renderApp();

    expect(await screen.findByRole("heading", { name: "Create the admin account" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
    expect(screen.getByLabelText("Password").getAttribute("type")).toBe("password");
  });

  it("creates the admin account and signs in", async () => {
    let created = false;
    const { calls } = api({
      "GET /api/v1/auth/setup": () => json({ required: !created }),
      "POST /api/v1/auth/setup": () => {
        created = true;
        return json(alice, 201);
      },
      "GET /api/v1/auth/me": () => (created ? json(alice) : unauthorized()),
    });

    renderApp();
    await screen.findByRole("heading", { name: "Create the admin account" });
    await fillCredentials("alice", "correct horse");
    await userEvent.click(screen.getByRole("button", { name: "Create admin account" }));

    expect(await screen.findByText("Signed in as alice")).toBeTruthy();
    const post = calls.find((c) => c.method === "POST" && c.path === "/api/v1/auth/setup");
    expect(post?.body).toEqual({ name: "alice", password: "correct horse" });
    expect(post?.headers.get("Content-Type")).toBe("application/json");
  });

  it("rejects a short password without calling the API", async () => {
    const { calls } = api({ "GET /api/v1/auth/setup": () => json({ required: true }) });

    renderApp();
    await screen.findByRole("heading", { name: "Create the admin account" });
    await fillCredentials("alice", "short");
    await userEvent.click(screen.getByRole("button", { name: "Create admin account" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Password must be at least 8 characters",
    );
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("shows the server's message when setup is rejected", async () => {
    api({
      "GET /api/v1/auth/setup": () => json({ required: true }),
      "POST /api/v1/auth/setup": () => json({ detail: "name must not be blank" }, 422),
    });

    renderApp();
    await screen.findByRole("heading", { name: "Create the admin account" });
    await fillCredentials("alice", "correct horse");
    await userEvent.click(screen.getByRole("button", { name: "Create admin account" }));

    expect((await screen.findByRole("alert")).textContent).toContain("name must not be blank");
    expect(screen.queryByText(/Signed in as/)).toBeNull();
  });

  it("switches to sign in when someone else finished setup first", async () => {
    let done = false;
    api({
      "GET /api/v1/auth/setup": () => json({ required: !done }),
      "POST /api/v1/auth/setup": () => {
        done = true;
        return json({ detail: "Already configured" }, 409);
      },
      "GET /api/v1/auth/me": unauthorized,
    });

    renderApp();
    await screen.findByRole("heading", { name: "Create the admin account" });
    await fillCredentials("alice", "correct horse");
    await userEvent.click(screen.getByRole("button", { name: "Create admin account" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("doesn't warn about the password before the form is submitted", async () => {
    api({ "GET /api/v1/auth/setup": () => json({ required: true }) });

    renderApp();
    await screen.findByRole("heading", { name: "Create the admin account" });
    await userEvent.type(screen.getByLabelText("Password"), "short");

    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows a readable message for validation errors", async () => {
    api({
      "GET /api/v1/auth/setup": () => json({ required: true }),
      "POST /api/v1/auth/setup": () =>
        json({ detail: [{ type: "string_too_long", loc: ["body", "name"], msg: "too long" }] }, 422),
    });

    renderApp();
    await screen.findByRole("heading", { name: "Create the admin account" });
    await fillCredentials("alice", "correct horse");
    await userEvent.click(screen.getByRole("button", { name: "Create admin account" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Check the name and password.");
    expect(alert.textContent).not.toContain("[object Object]");
  });
});

describe("sign in", () => {
  it("shows the sign-in screen when not signed in", async () => {
    api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": unauthorized,
    });

    renderApp();

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
    expect(screen.getByLabelText("Password").getAttribute("type")).toBe("password");
    expect(screen.queryByText(/Signed in as/)).toBeNull();
  });

  it("skips the sign-in screen when the session is still valid", async () => {
    api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": () => json(alice),
    });

    renderApp();

    expect(await screen.findByText("Signed in as alice")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
  });

  it("signs in with a name and password", async () => {
    let signedIn = false;
    const { calls } = api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": () => (signedIn ? json(alice) : unauthorized()),
      "POST /api/v1/auth/login": () => {
        signedIn = true;
        return json(alice);
      },
    });

    renderApp();
    await screen.findByRole("heading", { name: "Sign in" });
    await fillCredentials("alice", "correct horse");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Signed in as alice")).toBeTruthy();
    const post = calls.find((c) => c.method === "POST" && c.path === "/api/v1/auth/login");
    expect(post?.body).toEqual({ name: "alice", password: "correct horse" });
    expect(post?.headers.get("Content-Type")).toBe("application/json");
  });

  it("shows an error for a wrong password and stays on the form", async () => {
    api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": unauthorized,
      "POST /api/v1/auth/login": () => json({ detail: "Invalid name or password" }, 401),
    });

    renderApp();
    await screen.findByRole("heading", { name: "Sign in" });
    await fillCredentials("alice", "wrong password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Invalid name or password");
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("signs out and returns to the sign-in screen", async () => {
    let signedIn = true;
    const { calls } = api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": () => (signedIn ? json(alice) : unauthorized()),
      "POST /api/v1/auth/logout": () => {
        signedIn = false;
        return noContent();
      },
    });

    renderApp();
    await screen.findByText("Signed in as alice");
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
    expect(screen.queryByText(/Signed in as/)).toBeNull();
    expect(calls.some((c) => c.method === "POST" && c.path === "/api/v1/auth/logout")).toBe(true);
  });

  it("can sign in again after signing out", async () => {
    let signedIn = true;
    api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": () => (signedIn ? json(alice) : unauthorized()),
      "POST /api/v1/auth/logout": () => {
        signedIn = false;
        return noContent();
      },
      "POST /api/v1/auth/login": () => {
        signedIn = true;
        return json(alice);
      },
    });

    renderApp();
    await screen.findByText("Signed in as alice");
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await screen.findByRole("heading", { name: "Sign in" });
    await fillCredentials("alice", "correct horse");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Signed in as alice")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
  });

  it("says when the server can't be reached while checking the session", async () => {
    api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": () => {
        throw new TypeError("Failed to fetch");
      },
    });

    renderApp();

    expect((await screen.findByRole("alert")).textContent).toMatch(/can[’']t reach the server/i);
    expect(screen.queryByLabelText("Password")).toBeNull();
  });

  it("doesn't flash the sign-in form while the session is being checked", async () => {
    const { calls } = api({
      "GET /api/v1/auth/setup": () => json({ required: false }),
      "GET /api/v1/auth/me": () => new Promise<Response>(() => {}),
    });

    renderApp();
    await waitFor(() => expect(calls.some((c) => c.path === "/api/v1/auth/me")).toBe(true));

    expect(screen.queryByRole("heading", { name: "Sign in" })).toBeNull();
    expect(screen.queryByLabelText("Password")).toBeNull();
  });

  it("says when the server can't be reached instead of showing a form", async () => {
    api({
      "GET /api/v1/auth/setup": () => {
        throw new TypeError("Failed to fetch");
      },
    });

    renderApp();

    expect((await screen.findByRole("alert")).textContent).toMatch(/can[’']t reach the server/i);
    await waitFor(() => {
      expect(screen.queryByLabelText("Password")).toBeNull();
    });
  });
});
