export interface ProxyOptions {
  service: string;
  path: string[];
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

export interface ProxyResult {
  data: unknown;
  status: number;
  ok: boolean;
}

export async function proxyRequest(
  baseUrl: string,
  targetPath: string,
  apiKey: string,
  options: ProxyOptions
): Promise<ProxyResult> {
  const url = `${baseUrl.replace(/\/+$/, "")}/${targetPath
    .map((p) => p.replace(/^\/+/, ""))
    .join("/")}`;

  const headers: Record<string, string> = {
    "Accept": "application/json",
    ...options.headers,
  };

  const apiKeyPrefix = baseUrl.includes("qbittorrent")
    ? apiKey
    : `Apikey ${apiKey}`;

  headers["X-Api-Key"] = apiKeyPrefix || apiKey;

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const data = await response.json().catch(() => ({}));

  return {
    data,
    status: response.status,
    ok: response.ok,
  };
}

export async function checkHealth(
  baseUrl: string,
  apiKey: string,
  healthPath: string
): Promise<{ status: string; ok: boolean }> {
  try {
    const url = `${baseUrl.replace(/\/+$/, "")}${healthPath}`;
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Accept": "application/json",
        "X-Api-Key": baseUrl.includes("qbittorrent")
          ? "default"
          : `Apikey ${apiKey}` || "default",
      },
    });

    return {
      status: response.ok ? "online" : "error",
      ok: response.ok,
    };
  } catch {
    return { status: "offline", ok: false };
  }
}
