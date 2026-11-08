import { describe, expect, it } from "vitest";

import config from "../vite.config";

describe("vite config", () => {
  it("proxies /api to the backend", () => {
    expect(config.server?.proxy?.["/api"]).toMatchObject({ target: "http://localhost:8000" });
  });
});
