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
  onAuthFailure?: () => void;
  query?: Record<string, string | number | boolean | null | undefined>;
  refreshAccessToken?: AccessTokenProvider;
  responseType?: "json" | "text" | "void";
};

export async function apiFetch<T>(
  path: string,
  {
    auth = true,
    body,
    getAccessToken,
    headers,
    onAuthFailure,
    query,
    refreshAccessToken,
    responseType = "json",
    ...init
  }: ApiFetchOptions = {},
): Promise<T> {
  const initialToken = auth && getAccessToken ? await getAccessToken() : null;
  let response = await sendRequest(initialToken);

  if (response.status === 401 && auth && refreshAccessToken) {
    const refreshedToken = await refreshAccessToken();

    if (refreshedToken) {
      response = await sendRequest(refreshedToken);
    }
  }

  if (response.status === 401 && auth) {
    onAuthFailure?.();
  }

  async function sendRequest(token: string | null | undefined) {
    const requestHeaders = new Headers(headers);

    if (body && isJsonBody(body) && !requestHeaders.has("Content-Type")) {
      requestHeaders.set("Content-Type", "application/json");
    }

    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }

    return fetch(buildApiUrl(path, query, getApiBaseUrl()), {
      ...init,
      body: serializeBody(body),
      headers: requestHeaders,
    });
  }

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
