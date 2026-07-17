export { apiFetch } from "@/lib/api/client";
export type { AccessTokenProvider, ApiFetchOptions } from "@/lib/api/client";
export { loginUser, refreshSession, registerUser } from "@/lib/api/auth";
export type { AuthCredentials } from "@/lib/api/auth";
export { getApiBaseUrl } from "@/lib/api/config";
export { ApiError, isApiError } from "@/lib/api/errors";
export type { ApiErrorDetail } from "@/lib/api/errors";
export { getHealth } from "@/lib/api/health";
export { createPaper, deletePaper, updatePaper } from "@/lib/api/papers";
export type { PaperMutationPayload } from "@/lib/api/papers";
export { searchPapers } from "@/lib/api/search";
export type { SearchPapersParams, SearchScope } from "@/lib/api/search";
export type {
  Collection,
  HealthResponse,
  PaginationResponse,
  Paper,
  PaperListItem,
  Token,
  User,
} from "@/lib/api/types";
