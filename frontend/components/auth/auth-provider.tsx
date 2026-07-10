"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
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
  clearStoredTokens,
  getStoredTokens,
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
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [tokens, setTokens] = useState<StoredTokens | null>(() => {
    const storedTokens = getStoredTokens();
    return storedTokens;
  });
  const [status, setStatus] = useState<AuthStatus>(() => {
    return getStoredTokens() ? "authenticated" : "guest";
  });

  const logout = useCallback(() => {
    clearStoredTokens();
    setTokens(null);
    setStatus("guest");
    router.push("/login");
  }, [router]);

  const persistTokenPair = useCallback((tokenPair: Parameters<typeof storeTokens>[0]) => {
    const nextTokens = storeTokens(tokenPair);
    setTokens(nextTokens);
    setStatus("authenticated");
  }, []);

  const login = useCallback(
    async (credentials: AuthCredentials) => {
      const tokenPair = await loginUser(credentials);
      persistTokenPair(tokenPair);
    },
    [persistTokenPair],
  );

  const register = useCallback(
    async (credentials: AuthCredentials) => {
      await registerUser(credentials);
      const tokenPair = await loginUser(credentials);
      persistTokenPair(tokenPair);
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
      setTokens(nextTokens);
      setStatus("authenticated");
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
    }),
    [apiRequest, getAccessToken, login, logout, register, status, tokens],
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
