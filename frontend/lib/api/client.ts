import { buildApiUrl, getApiBaseUrl } from "@/lib/api/config";
import { ApiError } from "@/lib/api/errors";

export type AccessTokenProvider = () =>
  | string
  | null
  | undefined
  | Promise<string | null | undefined>;

type JsonBody = Record<string, unknown> | unknown[];

export type ApiFetchOptions = Omit<RequestInit, "body"> & {
  auth?: boolean;
  body?: BodyInit | JsonBody | null;
  getAccessToken?: AccessTokenProvider;
  query?: Record<string, string | number | boolean | null | undefined>;
  responseType?: "json" | "text" | "void";
};

export async function apiFetch<T>(
  path: string,
  {
    auth = true,
    body,
    getAccessToken,
    headers,
    query,
    responseType = "json",
    ...init
  }: ApiFetchOptions = {},
): Promise<T> {
  const requestHeaders = new Headers(headers);

  if (body && isJsonBody(body) && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (auth && getAccessToken) {
    const token = await getAccessToken();

    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(buildApiUrl(path, query, getApiBaseUrl()), {
    ...init,
    body: serializeBody(body),
    headers: requestHeaders,
  });

  if (!response.ok) {
    throw await createApiError(response);
  }

  if (response.status === 204 || responseType === "void") {
    return undefined as T;
  }

  if (responseType === "text") {
    return (await response.text()) as T;
  }

  return (await response.json()) as T;
}

async function createApiError(response: Response): Promise<ApiError> {
  const data = await readErrorBody(response);
  const detail = getErrorDetail(data);

  return new ApiError({
    status: response.status,
    statusText: response.statusText,
    detail,
    data,
  });
}

async function readErrorBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("Content-Type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

function getErrorDetail(data: unknown): unknown {
  if (data && typeof data === "object" && "detail" in data) {
    return data.detail;
  }

  return data;
}

function isJsonBody(body: BodyInit | JsonBody): body is JsonBody {
  return (
    typeof body === "object" &&
    body !== null &&
    !(body instanceof FormData) &&
    !(body instanceof URLSearchParams) &&
    !(body instanceof Blob) &&
    !(body instanceof ArrayBuffer) &&
    !ArrayBuffer.isView(body) &&
    !(body instanceof ReadableStream)
  );
}

function serializeBody(body: BodyInit | JsonBody | null | undefined) {
  if (!body || !isJsonBody(body)) {
    return body;
  }

  return JSON.stringify(body);
}
