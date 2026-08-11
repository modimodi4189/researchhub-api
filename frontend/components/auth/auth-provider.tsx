"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";
import { useRouter } from "next/navigation";
import { apiFetch, type ApiFetchOptions } from "@/lib/api";
import {
  loginUser,
  refreshSession,
  registerUser,
  type AuthCredentials,
} from "@/lib/api/auth";
import {
  AUTH_STORAGE_EVENT,
  clearStoredTokens,
  getStoredTokens,
  getStoredUserEmail,
  storeTokens,
  type StoredTokens,
} from "@/lib/auth/storage";

type AuthStatus = "loading" | "authenticated" | "guest";

type AuthContextValue = {
  apiRequest: <T>(path: string, options?: ApiFetchOptions) => Promise<T>;
  getAccessToken: () => string | null;
  login: (credentials: AuthCredentials) => Promise<void>;
  logout: () => void;
  register: (credentials: AuthCredentials) => Promise<void>;
  status: AuthStatus;
  tokens: StoredTokens | null;
  userEmail: string | null;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const hasHydrated = useSyncExternalStore(
    subscribeToHydration,
    getHydratedSnapshot,
    getServerHydratedSnapshot,
  );
  const tokenSnapshot = useSyncExternalStore(
    subscribeToStoredTokens,
    getStoredTokenSnapshot,
    getServerTokenSnapshot,
  );
  const tokens = useMemo(() => parseTokenSnapshot(tokenSnapshot), [tokenSnapshot]);
  const userEmail = useMemo(() => parseUserEmailSnapshot(tokenSnapshot), [tokenSnapshot]);
  const status: AuthStatus = !hasHydrated
    ? "loading"
    : tokens
      ? "authenticated"
      : "guest";

  const logout = useCallback(() => {
    clearStoredTokens();
    router.push("/login");
  }, [router]);

  const persistTokenPair = useCallback((tokenPair: Parameters<typeof storeTokens>[0], userEmail: string) => {
    storeTokens(tokenPair, userEmail);
  }, []);

  const login = useCallback(
    async (credentials: AuthCredentials) => {
      const tokenPair = await loginUser(credentials);
      persistTokenPair(tokenPair, credentials.email);
    },
    [persistTokenPair],
  );

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      await registerUser(credentials);
      const tokenPair = await loginUser(credentials);
      persistTokenPair(tokenPair, credentials.email);
    },
    [persistTokenPair],
  );

  const getAccessToken = useCallback(() => {
    return tokens?.accessToken ?? getStoredTokens()?.accessToken ?? null;
  }, [tokens]);

  const refreshAccessToken = useCallback(async () => {
    const refreshToken = tokens?.refreshToken ?? getStoredTokens()?.refreshToken;

    if (!refreshToken) {
      return null;
    }

    try {
      const tokenPair = await refreshSession(refreshToken);
      const nextTokens = storeTokens(tokenPair);
      return nextTokens.accessToken;
    } catch {
      logout();
      return null;
    }
  }, [logout, tokens]);

  const apiRequest = useCallback(
    <T,>(path: string, options: ApiFetchOptions = {}) => {
      return apiFetch<T>(path, {
        ...options,
        getAccessToken,
        onAuthFailure: logout,
        refreshAccessToken,
      });
    },
    [getAccessToken, logout, refreshAccessToken],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      apiRequest,
      getAccessToken,
      login,
      logout,
      register,
      status,
      tokens,
      userEmail,
    }),
    [apiRequest, getAccessToken, login, logout, register, status, tokens, userEmail],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}

function subscribeToHydration(onStoreChange: () => void) {
  queueMicrotask(onStoreChange);
  return () => {};
}

function getHydratedSnapshot() {
  return true;
}

function getServerHydratedSnapshot() {
  return false;
}

function subscribeToStoredTokens(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(AUTH_STORAGE_EVENT, onStoreChange);

  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(AUTH_STORAGE_EVENT, onStoreChange);
  };
}

function getStoredTokenSnapshot() {
  const tokens = getStoredTokens();

  if (!tokens) {
    return null;
  }

  return `${tokens.accessToken}\n${tokens.refreshToken}\n${getStoredUserEmail() ?? ""}`;
}

function getServerTokenSnapshot() {
  return null;
}

function parseTokenSnapshot(snapshot: string | null): StoredTokens | null {
  if (!snapshot) {
    return null;
  }

  const [accessToken, refreshToken] = snapshot.split("\n");

  if (!accessToken || !refreshToken) {
    return null;
  }

  return { accessToken, refreshToken };
}

function parseUserEmailSnapshot(snapshot: string | null): string | null {
  if (!snapshot) {
    return null;
  }

  const [, , userEmail] = snapshot.split("\n");
  return userEmail || null;
}
