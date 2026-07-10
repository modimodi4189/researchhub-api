"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useAuth();

  useEffect(() => {
    if (status === "guest") {
      router.replace(
        `/login?next=${encodeURIComponent(pathname)}&reason=auth_required`,
      );
    }
  }, [pathname, router, status]);

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas text-ink">
        <div className="flex items-center gap-3 rounded-md border border-border bg-surface px-4 py-3 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          {status === "loading" ? "Checking session" : "Redirecting to sign in"}
        </div>
      </main>
    );
  }

  return children;
}
