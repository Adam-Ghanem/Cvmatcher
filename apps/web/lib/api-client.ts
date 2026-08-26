export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    requestId: string;
  };
}

export interface CurrentUser {
  id: string;
  email: string;
  createdAt: string;
}

export interface AuthenticatedUserResponse {
  user: CurrentUser;
}

export interface CsrfTokenResponse {
  csrfToken: string;
}

export interface CvDocumentVersion {
  id: string;
  versionNumber: number;
  originalFilename: string;
  contentType: string;
  byteSize: number;
  uploadedAt: string;
}

export interface CvDocument {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  latestVersion: CvDocumentVersion;
}

export interface CvDocumentListResponse {
  data: CvDocument[];
}

export interface CreateJobTargetInput {
  title: string;
  company?: string;
  location?: string;
  jobDescription: string;
}

export interface JobTarget {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  jobDescriptionCharacterCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface JobTargetListResponse {
  data: JobTarget[];
}

export interface MatchScoreComponent {
  key: string;
  label: string;
  weight: number;
  score: number;
  state: "MATCHED" | "PARTIAL" | "EVIDENCE_NOT_FOUND" | "NOT_APPLICABLE";
  matchedTerms: string[];
  notFoundTerms: string[];
  explanation: string;
}

export interface MatchGap {
  term: string;
  state: "NOT_FOUND_IN_PROVIDED_CV";
  component: string;
}

export interface MatchAnalysis {
  id: string;
  scoringVersion: string;
  overallScore: number;
  components: MatchScoreComponent[];
  gaps: MatchGap[];
  createdAt: string;
}

export type CvExtractionStatus = "pending" | "processing" | "succeeded" | "failed";

export interface CvExtraction {
  id: string;
  status: CvExtractionStatus;
  sourceType: "pdf" | "docx";
  characterCount: number;
  completedAt: string | null;
  failureMessage: string | null;
}

export class ApiRequestError extends Error {
  public readonly code: string;
  public readonly requestId: string;

  public constructor(error: ApiErrorBody["error"], public readonly status: number) {
    super(error.message);
    this.name = "ApiRequestError";
    this.code = error.code;
    this.requestId = error.requestId;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (!value || typeof value !== "object" || !("error" in value)) {
    return false;
  }

  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error &&
    "requestId" in error &&
    typeof error.code === "string" &&
    typeof error.message === "string" &&
    typeof error.requestId === "string"
  );
}

export function apiUrl(path: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return new URL(path, baseUrl).toString();
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const requestId = crypto.randomUUID();
  const response = await fetch(apiUrl(path), {
    credentials: "include",
    ...init,
    headers: {
      Accept: "application/json",
      "X-Request-ID": requestId,
      ...init.headers,
    },
  });

  const hasJsonBody = response.headers.get("content-type")?.includes("application/json") ?? false;
  const body: unknown = hasJsonBody ? await response.json() : undefined;
  if (!response.ok) {
    if (isApiErrorBody(body)) {
      throw new ApiRequestError(body.error, response.status);
    }
    throw new ApiRequestError(
      {
        code: "UNEXPECTED_RESPONSE",
        message: "We could not complete this request. Please try again.",
        requestId,
      },
      response.status,
    );
  }

  return body as T;
}

export async function getCsrfToken(): Promise<string> {
  const response = await apiFetch<CsrfTokenResponse>("/api/v1/auth/csrf");
  return response.csrfToken;
}

export async function listJobTargets(): Promise<JobTargetListResponse> {
  return apiFetch<JobTargetListResponse>("/api/v1/job-targets");
}

export async function createJobTarget(input: CreateJobTargetInput): Promise<JobTarget> {
  const csrfToken = await getCsrfToken();
  return apiFetch<JobTarget>("/api/v1/job-targets", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(input),
  });
}

export async function createMatchAnalysis(input: {
  cvDocumentVersionId: string;
  jobTargetId: string;
}): Promise<MatchAnalysis> {
  const csrfToken = await getCsrfToken();
  return apiFetch<MatchAnalysis>("/api/v1/match-analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(input),
  });
}

export async function getMatchAnalysis(analysisId: string): Promise<MatchAnalysis> {
  return apiFetch<MatchAnalysis>(`/api/v1/match-analyses/${analysisId}`);
}

function cvExtractionPath(documentId: string, versionId: string): string {
  return `/api/v1/cv-documents/${documentId}/versions/${versionId}/extraction`;
}

export async function getCvExtraction(
  documentId: string,
  versionId: string,
): Promise<CvExtraction> {
  return apiFetch<CvExtraction>(cvExtractionPath(documentId, versionId));
}

export async function createCvExtraction(
  documentId: string,
  versionId: string,
): Promise<CvExtraction> {
  const csrfToken = await getCsrfToken();
  return apiFetch<CvExtraction>(cvExtractionPath(documentId, versionId), {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}


export async function deleteCvDocument(documentId: string): Promise<void> {
  const csrfToken = await getCsrfToken();
  await apiFetch<void>(`/api/v1/cv-documents/${documentId}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export async function deleteJobTarget(targetId: string): Promise<void> {
  const csrfToken = await getCsrfToken();
  await apiFetch<void>(`/api/v1/job-targets/${targetId}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}
