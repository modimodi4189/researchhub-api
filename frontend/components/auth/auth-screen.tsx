import { Sparkles } from "lucide-react";
import { AuthForm } from "@/components/auth/auth-form";
import { ApiHealthStatus } from "@/components/api-health-status";

type AuthScreenProps = {
  mode: "login" | "register";
};

export function AuthScreen({ mode }: AuthScreenProps) {
  return (
    <main className="min-h-screen bg-canvas text-ink">
      <div className="grid min-h-screen grid-cols-[minmax(420px,520px)_1fr]">
        <section className="flex flex-col justify-between border-r border-border bg-surface px-10 py-8">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-md border border-border bg-background text-primary">
              <Sparkles className="size-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight">ResearchHub</p>
              <p className="text-xs text-muted-foreground">Research workspace</p>
            </div>
          </div>

          <div className="max-w-sm">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
              Auth foundation
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">
              A quiet front door for focused research work.
            </h1>
            <p className="mt-4 text-sm leading-6 text-muted-foreground">
              This pass handles accounts, token storage, route protection, and
              logout so the paper library can be built on authenticated ground.
            </p>
          </div>

          <ApiHealthStatus />
        </section>

        <section className="flex items-center justify-center px-12 py-10">
          <AuthForm mode={mode} />
        </section>
      </div>
    </main>
  );
}
