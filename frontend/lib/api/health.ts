import { apiFetch } from "@/lib/api/client";
import type { HealthResponse } from "@/lib/api/types";

export function getHealth() {
  return apiFetch<HealthResponse>("/health", { auth: false });
}
