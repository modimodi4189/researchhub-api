import type { Token } from "@/lib/api/types";

const ACCESS_TOKEN_KEY = "researchhub.accessToken";
const REFRESH_TOKEN_KEY = "researchhub.refreshToken";
const USER_EMAIL_KEY = "researchhub.userEmail";

export const AUTH_STORAGE_EVENT = "researchhub:auth-storage";

export type StoredTokens = {
  accessToken: string;
  refreshToken: string;
};

export function getStoredTokens(): StoredTokens | null {
  if (typeof window === "undefined") {
    return null;
  }

  const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);

  if (!accessToken || !refreshToken) {
    return null;
  }

  return { accessToken, refreshToken };
}

export function getStoredUserEmail(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(USER_EMAIL_KEY);
}

export function storeTokens(token: Token, userEmail?: string): StoredTokens {
  const storedTokens = {
    accessToken: token.access_token,
    refreshToken: token.refresh_token,
  };

  if (typeof window !== "undefined") {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, storedTokens.accessToken);
    window.localStorage.setItem(REFRESH_TOKEN_KEY, storedTokens.refreshToken);

    if (userEmail) {
      window.localStorage.setItem(USER_EMAIL_KEY, userEmail);
    }

    emitAuthStorageChange();
  }

  return storedTokens;
}

export function clearStoredTokens() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_EMAIL_KEY);
  emitAuthStorageChange();
}

function emitAuthStorageChange() {
  window.dispatchEvent(new Event(AUTH_STORAGE_EVENT));
}
