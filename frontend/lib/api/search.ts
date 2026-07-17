import { apiFetch, type ApiFetchOptions } from "@/lib/api/client";
import type { PaginationResponse, PaperListItem } from "@/lib/api/types";

export type SearchScope = "my" | "public";

export type SearchPapersParams = {
  k: number;
  q: string;
  scope: SearchScope;
};

export function searchPapers(
  { k, q, scope }: SearchPapersParams,
  options?: ApiFetchOptions,
) {
  return apiFetch<PaginationResponse<PaperListItem>>(
    `/api/v1/search/${scope}`,
    {
      ...options,
      query: { q, k },
    },
  );
}
