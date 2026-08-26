import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    apiFetch: vi.fn(),
    createCvExtraction: vi.fn(),
    getCvExtraction: vi.fn(),
  };
});

import { CvWorkspace } from "@/components/app/CvWorkspace";
import { apiFetch, createCvExtraction, getCvExtraction } from "@/lib/api-client";

const document = {
  id: "document-id",
  title: "Candidate CV",
  createdAt: "2026-08-26T00:00:00Z",
  updatedAt: "2026-08-26T00:00:00Z",
  latestVersion: {
    id: "version-id",
    versionNumber: 1,
    originalFilename: "candidate-cv.docx",
    contentType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    byteSize: 1_024,
    uploadedAt: "2026-08-26T00:00:00Z",
  },
};

describe("CvWorkspace", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("gives a saved CV an explicit preparation action with a privacy-preserving explanation", async () => {
    vi.mocked(apiFetch).mockImplementation((path) => {
      if (path === "/api/v1/auth/me") {
        return Promise.resolve({
          user: {
            createdAt: "2026-08-26T00:00:00Z",
            email: "candidate@example.com",
            id: "user-id",
          },
        });
      }
      if (path === "/api/v1/cv-documents") {
        return Promise.resolve({ data: [document] });
      }
      return Promise.reject(new Error(`Unexpected request: ${path}`));
    });

    vi.mocked(getCvExtraction).mockRejectedValue({ status: 404 });
    vi.mocked(createCvExtraction).mockResolvedValue({
      characterCount: 23,
      completedAt: "2026-08-26T00:00:01Z",
      failureMessage: null,
      id: "extraction-id",
      sourceType: "docx",
      status: "succeeded",
    });

    render(<CvWorkspace />);

    const prepareButton = await screen.findByRole("button", { name: "Prepare CV text" });
    expect(screen.getByText(/private text is kept on the server/i)).toBeInTheDocument();

    fireEvent.click(prepareButton);

    await waitFor(() => {
      expect(createCvExtraction).toHaveBeenCalledWith("document-id", "version-id");
      expect(screen.getByText("Text prepared")).toBeInTheDocument();
    });
  });
});
