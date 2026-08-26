import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "@/lib/api-client";

describe("apiFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("raises a typed error from the shared API error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "DEPENDENCY_UNAVAILABLE",
              message: "The service is not ready. Please try again shortly.",
              requestId: "3f79e747-17ab-4c80-9e5a-4a9e438471f8",
            },
          }),
          { status: 503 },
        ),
      ),
    );

    await expect(apiFetch("/api/v1/ready")).rejects.toMatchObject({
      code: "DEPENDENCY_UNAVAILABLE",
      requestId: "3f79e747-17ab-4c80-9e5a-4a9e438471f8",
      status: 503,
    });
  });
});
