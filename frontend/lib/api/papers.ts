import { apiFetch, type ApiFetchOptions } from "@/lib/api/client";
import type { Paper } from "@/lib/api/types";

export type PaperMutationPayload = {
  title: string;
  abstract: string | null;
  content: string | null;
  is_public: boolean;
  category_id: number | null;
};

export function createPaper(
  payload: PaperMutationPayload,
  options?: ApiFetchOptions,
) {
  return apiFetch<Paper>("/api/v1/papers", {
    ...options,
    method: "POST",
    body: payload,
  });
}

export function updatePaper(
  paperId: number,
  payload: PaperMutationPayload,
  options?: ApiFetchOptions,
) {
  return apiFetch<Paper>(`/api/v1/papers/${paperId}`, {
    ...options,
    method: "PATCH",
    body: payload,
  });
}
