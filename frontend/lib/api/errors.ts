export type ApiErrorDetail =
  | string
  | Array<{
      loc?: Array<string | number>;
      msg?: string;
      type?: string;
    }>
  | unknown;

export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly detail: ApiErrorDetail;
  readonly data: unknown;

  constructor({
    status,
    statusText,
    detail,
    data,
  }: {
    status: number;
    statusText: string;
    detail: ApiErrorDetail;
    data: unknown;
  }) {
    super(formatApiErrorMessage(status, statusText, detail));
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.detail = detail;
    this.data = data;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

function formatApiErrorMessage(
  status: number,
  statusText: string,
  detail: ApiErrorDetail,
): string {
  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const firstMessage = detail.find(
      (item) => item && typeof item.msg === "string",
    )?.msg;

    if (firstMessage) {
      return firstMessage;
    }
  }

  return `Request failed with ${status} ${statusText}`;
}
