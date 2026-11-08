export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function extractDetail(body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (Array.isArray(detail)) return "Check the name and password.";
    if (typeof detail === "string") return detail;
  }
  return "";
}

export async function fetchApi(path: string, options?: RequestInit): Promise<unknown> {
  const hasBody = options?.body != null && options?.body !== "";

  try {
    const res = await fetch(path, {
      ...options,
      ...(hasBody ? { headers: { "Content-Type": "application/json" } } : {}),
    });

    if (!res.ok) {
      let message = "API error";
      try {
        const text = await res.text();
        if (text) {
          const body = JSON.parse(text);
          const detail = extractDetail(body);
          if (detail) message = detail;
        }
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, message);
    }

    if (res.status === 204) return null;

    const text = await res.text();
    if (!text) return null;
    return JSON.parse(text);
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof TypeError) {
      throw new ApiError(0, "Can't reach the server. Check that the backend is running.");
    }
    throw err;
  }
}
