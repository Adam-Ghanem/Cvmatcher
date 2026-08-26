export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    requestId: string;
  };
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

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const requestId = crypto.randomUUID();
  const response = await fetch(new URL(path, baseUrl), {
    ...init,
    headers: {
      Accept: "application/json",
      "X-Request-ID": requestId,
      ...init.headers,
    },
  });

  const body: unknown = await response.json();
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
