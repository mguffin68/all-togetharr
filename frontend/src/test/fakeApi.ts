import { vi } from "vitest";

export type FakeRequest = {
  method: string;
  path: string;
  search: URLSearchParams;
  headers: Headers;
  body: unknown;
};

/** Returns a Response, or throws to simulate a network failure. */
export type Handler = (req: FakeRequest) => Response | Promise<Response>;

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function noContent(): Response {
  return new Response(null, { status: 204 });
}

export const unauthorized = (): Response => json({ detail: "Not authenticated" }, 401);

export function healthy(version = "1.2.3"): Handler {
  return () => json({ status: "ok", version });
}

/**
 * Stubs global fetch with a router keyed by "METHOD /path" (no query string).
 * Unmatched requests get a 404 and are still recorded in `calls`.
 */
export function fakeApi(routes: Record<string, Handler>) {
  const calls: FakeRequest[] = [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = input instanceof Request ? input.url : String(input);
    const url = new URL(raw, "http://localhost");
    const method = (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
    const headers = new Headers(init?.headers ?? (input instanceof Request ? input.headers : {}));
    let body: unknown = undefined;
    if (typeof init?.body === "string") {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    const req: FakeRequest = { method, path: url.pathname, search: url.searchParams, headers, body };
    calls.push(req);

    const handler = routes[`${method} ${url.pathname}`];
    if (!handler) {
      return json({ detail: "Not Found" }, 404);
    }
    return handler(req);
  });

  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, calls };
}
