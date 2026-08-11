import { apiFetch, type ApiFetchOptions } from "@/lib/api/client";
import type {
  Collection,
  CollectionWithPapers,
  PaginationResponse,
} from "@/lib/api/types";

export type CollectionMutationPayload = {
  name: string;
};

export function listCollections(
  page = 1,
  limit = 50,
  options?: ApiFetchOptions,
) {
  return apiFetch<PaginationResponse<Collection>>("/api/v1/collections", {
    ...options,
    query: { page, limit },
  });
}

export function createCollection(
  payload: CollectionMutationPayload,
  options?: ApiFetchOptions,
) {
  return apiFetch<Collection>("/api/v1/collections", {
    ...options,
    method: "POST",
    body: payload,
  });
}

export function getCollection(collectionId: number, options?: ApiFetchOptions) {
  return apiFetch<CollectionWithPapers>(
    `/api/v1/collections/${collectionId}`,
    options,
  );
}

export function updateCollection(
  collectionId: number,
  payload: CollectionMutationPayload,
  options?: ApiFetchOptions,
) {
  return apiFetch<Collection>(`/api/v1/collections/${collectionId}`, {
    ...options,
    method: "PATCH",
    body: payload,
  });
}

export function deleteCollection(
  collectionId: number,
  options?: ApiFetchOptions,
) {
  return apiFetch<void>(`/api/v1/collections/${collectionId}`, {
    ...options,
    method: "DELETE",
    responseType: "void",
  });
}

export function addPaperToCollection(
  collectionId: number,
  paperId: number,
  options?: ApiFetchOptions,
) {
  return apiFetch<{ message: string }>(
    `/api/v1/collections/${collectionId}/papers/${paperId}`,
    {
      ...options,
      method: "POST",
    },
  );
}

export function removePaperFromCollection(
  collectionId: number,
  paperId: number,
  options?: ApiFetchOptions,
) {
  return apiFetch<void>(
    `/api/v1/collections/${collectionId}/papers/${paperId}`,
    {
      ...options,
      method: "DELETE",
      responseType: "void",
    },
  );
}
