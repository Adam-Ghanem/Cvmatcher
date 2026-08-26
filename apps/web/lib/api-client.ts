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
