"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChangeEvent, useCallback, useEffect, useRef, useState } from "react";

import { CvExtractionControl } from "@/components/app/CvExtractionControl";
import {
  ApiRequestError,
  apiFetch,
  apiUrl,
  createCvExtraction,
  CvDocument,
  CvDocumentListResponse,
  CvExtraction,
  CurrentUser,
  getCsrfToken,
  getCvExtraction,
} from "@/lib/api-client";

type UploadState = "idle" | "uploading" | "complete";

interface UploadApiError {
  error?: { code?: string; message?: string; requestId?: string };
}

function readableSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(value),
  );
}

function safeUploadMessage(response: XMLHttpRequest): string {
  try {
    const parsed = JSON.parse(response.responseText) as UploadApiError;
    if (typeof parsed.error?.message === "string") {
      return parsed.error.message;
    }
  } catch {
    // The backend may fail before it can return its typed error response.
  }
  return "We could not upload this CV. Check the file and try again.";
}

export function CvWorkspace() {
  const router = useRouter();
  const uploadInputRef = useRef<HTMLInputElement>(null);
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [documents, setDocuments] = useState<CvDocument[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [extractions, setExtractions] = useState<Record<string, CvExtraction | null>>({});
  const [extractionErrors, setExtractionErrors] = useState<Record<string, string>>({});
  const [startingVersionId, setStartingVersionId] = useState<string | null>(null);

  const fetchWorkspace = useCallback(async () => {
    return Promise.all([
      apiFetch<{ user: CurrentUser }>("/api/v1/auth/me"),
      apiFetch<CvDocumentListResponse>("/api/v1/cv-documents"),
    ]);
  }, []);

  const loadExtractionStatus = useCallback(async (document: CvDocument) => {
    const versionId = document.latestVersion.id;
    try {
      const extraction = await getCvExtraction(document.id, versionId);
      setExtractions((currentExtractions) => ({ ...currentExtractions, [versionId]: extraction }));
      setExtractionErrors((currentErrors) => {
        const remainingErrors = { ...currentErrors };
        delete remainingErrors[versionId];
        return remainingErrors;
      });
    } catch (requestError) {
      if (requestError instanceof ApiRequestError && requestError.status === 404) {
        setExtractions((currentExtractions) => ({ ...currentExtractions, [versionId]: null }));
        return;
      }
      setExtractionErrors((currentErrors) => ({
        ...currentErrors,
        [versionId]: "We could not check this CV’s preparation status. Refresh and try again.",
      }));
    }
  }, []);

  const loadExtractionStatuses = useCallback((currentDocuments: CvDocument[]) => {
    void Promise.all(currentDocuments.map((document) => loadExtractionStatus(document)));
  }, [loadExtractionStatus]);

  async function startExtraction(document: CvDocument) {
    const versionId = document.latestVersion.id;
    setStartingVersionId(versionId);
    setExtractionErrors((currentErrors) => {
      const remainingErrors = { ...currentErrors };
      delete remainingErrors[versionId];
      return remainingErrors;
    });
    try {
      const extraction = await createCvExtraction(document.id, versionId);
      setExtractions((currentExtractions) => ({ ...currentExtractions, [versionId]: extraction }));
    } catch (requestError) {
      setExtractionErrors((currentErrors) => ({
        ...currentErrors,
        [versionId]: requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not prepare this CV. Please try again.",
      }));
    } finally {
      setStartingVersionId(null);
    }
  }

  async function loadWorkspace() {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [identity, documentResponse] = await fetchWorkspace();
      setUser(identity.user);
      setDocuments(documentResponse.data);
      loadExtractionStatuses(documentResponse.data);
    } catch (requestError) {
      if (requestError instanceof ApiRequestError && requestError.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setLoadError(
        requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not load your private workspace. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    void fetchWorkspace()
      .then(([identity, documentResponse]) => {
        if (active) {
          setUser(identity.user);
          setDocuments(documentResponse.data);
          loadExtractionStatuses(documentResponse.data);
        }
      })
      .catch((requestError: unknown) => {
        if (!active) {
          return;
        }
        if (requestError instanceof ApiRequestError && requestError.status === 401) {
          router.replace("/auth/login");
          return;
        }
        setLoadError(
          requestError instanceof ApiRequestError
            ? requestError.message
            : "We could not load your private workspace. Please try again.",
        );
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [fetchWorkspace, loadExtractionStatuses, router]);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    setUploadError(null);
    setSelectedFile(file);
  }

  async function uploadSelectedFile() {
    if (!selectedFile) {
      setUploadError("Choose a PDF or DOCX CV before uploading.");
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setUploadError("This CV is larger than the 10 MiB upload limit.");
      return;
    }

    setUploadState("uploading");
    setUploadProgress(0);
    setUploadError(null);

    try {
      const csrfToken = await getCsrfToken();
      const uploadedDocument = await new Promise<CvDocument>((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open("POST", apiUrl("/api/v1/cv-documents"));
        request.withCredentials = true;
        request.setRequestHeader("Accept", "application/json");
        request.setRequestHeader("X-CSRF-Token", csrfToken);
        request.setRequestHeader("X-Request-ID", crypto.randomUUID());
        request.upload.addEventListener("progress", (event) => {
          if (event.lengthComputable) {
            setUploadProgress(Math.round((event.loaded / event.total) * 100));
          }
        });
        request.addEventListener("load", () => {
          if (request.status === 201) {
            resolve(JSON.parse(request.responseText) as CvDocument);
            return;
          }
          reject(new Error(safeUploadMessage(request)));
        });
        request.addEventListener("error", () => {
          reject(new Error("We could not reach CVMatcher. Check your connection and try again."));
        });
        const formData = new FormData();
        formData.append("file", selectedFile);
        request.send(formData);
      });
      setDocuments((currentDocuments) => [uploadedDocument, ...currentDocuments]);
      setUploadProgress(100);
      setUploadState("complete");
      setSelectedFile(null);
      if (uploadInputRef.current) {
        uploadInputRef.current.value = "";
      }
    } catch (error) {
      setUploadState("idle");
      setUploadError(error instanceof Error ? error.message : "We could not upload this CV. Please try again.");
    }
  }

  async function signOut() {
    try {
      const csrfToken = await getCsrfToken();
      await apiFetch<undefined>("/api/v1/auth/logout", {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken },
      });
    } finally {
      router.replace("/auth/login");
      router.refresh();
    }
  }

  return (
    <main className="min-h-screen bg-canvas px-4 py-4 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto min-h-[calc(100vh-2rem)] max-w-6xl rounded-md border border-line bg-surface shadow-panel">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line px-5 py-4 sm:px-8">
          <Link className="inline-flex items-center gap-3 font-semibold tracking-tight" href="/app">
            <span aria-hidden="true" className="grid size-8 place-items-center rounded-sm bg-brand text-sm font-bold text-white">
              C
            </span>
            <span>CVMatcher</span>
          </Link>
          <div className="flex items-center gap-3">
            <p className="hidden text-sm text-ink-muted sm:block">{user?.email ?? "Loading account…"}</p>
            <button
              className="rounded-sm border border-line px-3 py-2 text-sm font-semibold transition hover:border-brand hover:text-brand"
              onClick={() => void signOut()}
              type="button"
            >
              Sign out
            </button>
          </div>
        </header>

        <div className="grid gap-8 px-5 py-8 sm:px-8 lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-12 lg:px-14 lg:py-12">
          <section aria-labelledby="workspace-heading">
            <p className="text-sm font-semibold tracking-[0.16em] text-brand">YOUR CV LIBRARY</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl" id="workspace-heading">
              Start with the evidence you control.
            </h1>
            <p className="mt-4 max-w-2xl leading-7 text-ink-muted">
              Upload a PDF or DOCX CV to create a private versioned record. When you choose, CVMatcher can prepare private working text for a future analysis; the text is never displayed here.
            </p>

            <section className="mt-8 rounded-md border border-line bg-surface-subtle p-5 sm:p-6" aria-labelledby="upload-heading">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold" id="upload-heading">Upload a CV</h2>
                  <p className="mt-1 text-sm leading-6 text-ink-muted">PDF or DOCX only, up to 10 MiB. Files stay private to your account.</p>
                </div>
                <span className="w-fit rounded-sm bg-white px-2.5 py-1 text-xs font-semibold text-brand-strong">PRIVATE STORAGE</span>
              </div>

              <div className="mt-5 rounded-sm border border-dashed border-brand/50 bg-white p-4 sm:p-5">
                <label className="block text-sm font-semibold" htmlFor="cv-file">CV file</label>
                <input
                  accept="application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.pdf,.docx"
                  className="mt-3 block w-full text-sm file:mr-4 file:rounded-sm file:border-0 file:bg-brand file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-brand-strong"
                  id="cv-file"
                  onChange={chooseFile}
                  ref={uploadInputRef}
                  type="file"
                />
                {selectedFile ? <p className="mt-3 text-sm text-ink-muted">Ready to upload: <span className="font-semibold text-ink">{selectedFile.name}</span> · {readableSize(selectedFile.size)}</p> : null}
                {uploadState === "uploading" ? (
                  <div className="mt-4" aria-live="polite">
                    <div className="flex justify-between text-sm font-medium"><span>Uploading securely</span><span>{uploadProgress}%</span></div>
                    <progress className="mt-2 h-2 w-full accent-brand" max="100" value={uploadProgress}>{uploadProgress}%</progress>
                  </div>
                ) : null}
                {uploadError ? <p className="mt-4 rounded-sm border border-danger/30 bg-red-50 px-3 py-2 text-sm leading-6 text-danger" role="alert">{uploadError}</p> : null}
                {uploadState === "complete" ? <p className="mt-4 text-sm font-medium text-success" role="status">CV uploaded securely. It is ready when you are.</p> : null}
                <button
                  className="mt-5 rounded-sm bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={!selectedFile || uploadState === "uploading"}
                  onClick={() => void uploadSelectedFile()}
                  type="button"
                >
                  {uploadState === "uploading" ? "Uploading…" : "Save private CV"}
                </button>
              </div>
            </section>

            <section className="mt-10" aria-labelledby="documents-heading">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold tracking-[0.14em] text-brand">DOCUMENTS</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight" id="documents-heading">Your CV versions</h2>
                </div>
                <button className="text-sm font-semibold text-brand underline decoration-brand/40 underline-offset-4" onClick={() => void loadWorkspace()} type="button">Refresh</button>
              </div>

              {isLoading ? <div className="mt-5 space-y-3" aria-label="Loading CV documents"><div className="h-20 animate-pulse rounded-sm bg-surface-subtle" /><div className="h-20 animate-pulse rounded-sm bg-surface-subtle" /></div> : null}
              {loadError ? <div className="mt-5 rounded-sm border border-danger/30 bg-red-50 p-4 text-sm leading-6 text-danger" role="alert"><p>{loadError}</p><button className="mt-2 font-semibold underline underline-offset-4" onClick={() => void loadWorkspace()} type="button">Try again</button></div> : null}
              {!isLoading && !loadError && documents.length === 0 ? <div className="mt-5 rounded-md border border-line bg-surface-subtle p-6"><h3 className="font-semibold">No CVs saved yet</h3><p className="mt-2 max-w-xl text-sm leading-6 text-ink-muted">Your first upload creates a private, versioned starting point. When matching launches, you will choose exactly which version to use.</p><button className="mt-4 text-sm font-semibold text-brand underline decoration-brand/40 underline-offset-4" onClick={() => uploadInputRef.current?.click()} type="button">Choose your first CV</button></div> : null}
              {!isLoading && !loadError && documents.length > 0 ? (
                <ul className="mt-5 space-y-3">
                  {documents.map((document) => {
                    const versionId = document.latestVersion.id;
                    return (
                      <li className="rounded-sm border border-line bg-white p-4 sm:flex sm:items-center sm:justify-between sm:gap-4" key={document.id}>
                        <div>
                          <h3 className="font-semibold">{document.title}</h3>
                          <p className="mt-1 text-sm text-ink-muted">
                            {document.latestVersion.originalFilename} · Version {document.latestVersion.versionNumber} · {readableSize(document.latestVersion.byteSize)}
                          </p>
                          <p className="mt-3 text-sm text-ink-muted">Saved {formatDate(document.updatedAt)}</p>
                        </div>
                        <CvExtractionControl
                          document={document}
                          extraction={extractions[versionId]}
                          isStarting={startingVersionId === versionId}
                          onStart={startExtraction}
                          statusError={extractionErrors[versionId] ?? null}
                        />
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </section>
          </section>

          <aside className="self-start rounded-md border border-line bg-surface-subtle p-5" aria-labelledby="next-heading">
            <p className="text-sm font-semibold tracking-[0.14em] text-brand">WHAT’S NEXT</p>
            <h2 className="mt-2 text-xl font-semibold" id="next-heading">A clear path, not a black box.</h2>
            <ol className="mt-5 space-y-4 border-l border-brand pl-4 text-sm"><li><p className="font-semibold">1. Save your CV</p><p className="mt-1 leading-6 text-ink-muted">Create a private source of truth.</p></li><li><p className="font-semibold">2. Choose a target role</p><p className="mt-1 leading-6 text-ink-muted">Arrives in the next product phase.</p></li><li><p className="font-semibold">3. Understand the gap</p><p className="mt-1 leading-6 text-ink-muted">Only with visible evidence and actionable priorities.</p></li></ol>
          </aside>
        </div>
      </div>
    </main>
  );
}
