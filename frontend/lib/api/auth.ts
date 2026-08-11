import { apiFetch } from "@/lib/api/client";
import type { Token, User } from "@/lib/api/types";

export type AuthCredentials = {
  email: string;
  password: string;
};

export function registerUser(credentials: AuthCredentials) {
  return apiFetch<User>("/api/v1/auth/register", {
    auth: false,
    body: credentials,
    method: "POST",
  });
}

export function loginUser(credentials: AuthCredentials) {
  return apiFetch<Token>("/api/v1/auth/login", {
    auth: false,
    body: credentials,
    method: "POST",
  });
}

export function refreshSession(refreshToken: string) {
  return apiFetch<Token>("/api/v1/auth/refresh", {
    auth: false,
    body: { refresh_token: refreshToken },
    method: "POST",
  });
}
