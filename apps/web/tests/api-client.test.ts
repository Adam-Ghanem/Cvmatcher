import { afterEach, describe, expect, it, vi } from "vitest";

import {
  apiFetch,
  createCvExtraction,
  createJobTarget,
  getCvExtraction,
  listJobTargets,
} from "@/lib/api-client";

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
          { headers: { "content-type": "application/json" }, status: 503 },
        ),
      ),
    );

    await expect(apiFetch("/api/v1/ready")).rejects.toMatchObject({
      code: "DEPENDENCY_UNAVAILABLE",
      requestId: "3f79e747-17ab-4c80-9e5a-4a9e438471f8",
      status: 503,
    });
  });

  it("uses protected API contracts to create and retrieve an extraction status", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrfToken: "csrf-token" }), {
          headers: { "content-type": "application/json" },
          status: 200,
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "extraction-id", status: "processing" }), {
          headers: { "content-type": "application/json" },
          status: 200,
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "extraction-id", status: "succeeded" }), {
          headers: { "content-type": "application/json" },
          status: 200,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await createCvExtraction("document-id", "version-id");
    const extraction = await getCvExtraction("document-id", "version-id");

    const [createUrl, createInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(createUrl).toContain("/api/v1/cv-documents/document-id/versions/version-id/extraction");
    expect(createInit.method).toBe("POST");
    expect(createInit.headers).toMatchObject({ "X-CSRF-Token": "csrf-token" });
    expect(extraction.status).toBe("succeeded");
  });

  it("uses protected API contracts to save and list target roles without returning job text", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ csrfToken: "csrf-token" }), {
          headers: { "content-type": "application/json" },
          status: 200,
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "target-id", title: "Staff engineer" }), {
          headers: { "content-type": "application/json" },
          status: 201,
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ data: [{ id: "target-id", title: "Staff engineer" }] }), {
          headers: { "content-type": "application/json" },
          status: 200,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await createJobTarget({
      company: "Northstar Systems",
      jobDescription: "A private, untrusted job description that is long enough to test the request contract.",
      location: "Remote",
      title: "Staff engineer",
    });
    const targets = await listJobTargets();

    const [createUrl, createInit] = fetchMock.mock.calls[1] as [string, RequestInit];
    expect(createUrl).toContain("/api/v1/job-targets");
    expect(createInit.method).toBe("POST");
    expect(createInit.body).toContain("Staff engineer");
    expect(targets.data[0]?.title).toBe("Staff engineer");
  });

  it("sends browser credentials and a correlation identifier by default", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        headers: { "content-type": "application/json" },
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch<{ status: string }>("/api/v1/health");

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe("include");
    expect(init.headers).toMatchObject({ Accept: "application/json" });
    expect(init.headers).toHaveProperty("X-Request-ID");
  });
});
