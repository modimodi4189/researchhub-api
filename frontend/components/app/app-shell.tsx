"use client";

import type { ReactNode } from "react";
import {
  Bell,
  Compass,
  FolderKanban,
  Library,
  LogOut,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { ApiHealthStatus } from "@/components/api-health-status";
import { PaperLibrary } from "@/components/papers/paper-library";
import { Button } from "@/components/ui/button";

const navigation = [
  { name: "Library", icon: Library, href: "/app" },
  { name: "Search", icon: Search },
  { name: "Collections", icon: FolderKanban },
  { name: "Public Papers", icon: Compass },
  { name: "Settings", icon: Settings },
];

type AppShellProps = {
  activeNavigation?: string;
  children?: ReactNode;
  subtitle?: string;
  title?: string;
};

export function AppShell({
  activeNavigation = "Library",
  children,
  subtitle = "Authenticated papers loaded from the backend API.",
  title = "Library",
}: AppShellProps) {
  const { logout } = useAuth();

  return (
    <main className="min-h-screen bg-canvas text-ink">
      <div className="grid min-h-screen grid-cols-[264px_1fr]">
        <aside className="border-r border-border bg-sidebar px-4 py-5">
          <div className="mb-8 flex items-center gap-3 px-2">
            <div className="flex size-10 items-center justify-center rounded-md border border-border bg-surface text-primary">
              <Sparkles className="size-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">ResearchHub</p>
              <p className="text-xs text-muted-foreground">Research workspace</p>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="space-y-1">
            {navigation.map((item) => (
              <a
                key={item.name}
                href={
                  item.href ??
                  `#${item.name.toLowerCase().replaceAll(" ", "-")}`
                }
                className={`flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition ${
                  item.name === activeNavigation
                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-sidebar-accent/70 hover:text-foreground"
                }`}
              >
                <item.icon className="size-4" aria-hidden="true" />
                <span>{item.name}</span>
              </a>
            ))}
          </nav>

          <div className="mt-8 rounded-md border border-border bg-surface/70 p-3">
            <p className="text-xs font-medium text-foreground">Protected route</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              This shell is visible only after a local token pair is present.
            </p>
          </div>
        </aside>

        <section className="flex min-w-0 flex-col">
          <header className="flex h-16 items-center justify-between border-b border-border bg-background/80 px-7">
            <div>
              <p className="text-sm font-medium">{title}</p>
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            </div>
            <div className="flex items-center gap-3">
              <ApiHealthStatus />
              <Button
                type="button"
                variant="outline"
                size="icon-lg"
                aria-label="Notifications"
              >
                <Bell className="size-4" aria-hidden="true" />
              </Button>
              <Button type="button" variant="outline" onClick={logout}>
                <LogOut className="size-4" aria-hidden="true" />
                Logout
              </Button>
            </div>
          </header>

          <div className="flex-1 overflow-auto px-7 py-6">
            {children ?? <PaperLibrary />}
          </div>
        </section>
      </div>
    </main>
  );
}
