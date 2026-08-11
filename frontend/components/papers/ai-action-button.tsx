"use client";

import type { ComponentType, SVGProps } from "react";
import { AlertCircle, CheckCircle2, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type AiActionStatus = "idle" | "loading" | "success" | "error";

type AiActionButtonProps = {
  description: string;
  disabled?: boolean;
  endpointLabel: string;
  error?: string | null;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  loadingLabel: string;
  onClick: () => void;
  status: AiActionStatus;
  successMessage: string;
  title: string;
};

export function AiActionButton({
  description,
  disabled,
  endpointLabel,
  error,
  icon: Icon,
  loadingLabel,
  onClick,
  status,
  successMessage,
  title,
}: AiActionButtonProps) {
  const isLoading = status === "loading";
  const isSuccess = status === "success";
  const isError = status === "error";

  return (
    <div
      className={cn(
        "flex min-h-32 flex-col justify-between rounded-md border bg-card p-4 transition-colors",
        isLoading && "border-primary/40 bg-primary/5",
        isSuccess && "border-emerald-600/30 bg-emerald-600/5",
        isError && "border-destructive/40 bg-destructive/5",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex size-9 shrink-0 items-center justify-center rounded-md border border-border bg-background text-muted-foreground",
            isLoading && "border-primary/30 text-primary",
            isSuccess && "border-emerald-600/30 text-emerald-700",
            isError && "border-destructive/30 text-destructive",
          )}
        >
          {isLoading ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Icon className="size-4" aria-hidden="true" />
          )}
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">{title}</h3>
            <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[0.68rem] text-muted-foreground">
              {endpointLabel}
            </span>
          </div>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            {description}
          </p>
        </div>
      </div>

      <div className="mt-4 flex items-end justify-between gap-3">
        <div className="min-h-10 flex-1">
          {isLoading ? (
            <div className="text-sm">
              <p className="font-medium text-primary">{loadingLabel}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                This may take a minute. Waiting on backend AI processing, then
                fetching the latest paper data.
              </p>
            </div>
          ) : null}

          {isSuccess ? (
            <p className="flex items-center gap-1.5 text-sm font-medium text-emerald-700">
              <CheckCircle2 className="size-4" aria-hidden="true" />
              {successMessage}
            </p>
          ) : null}

          {isError && error ? (
            <p className="flex items-start gap-1.5 text-sm leading-5 text-destructive">
              <AlertCircle
                className="mt-0.5 size-4 shrink-0"
                aria-hidden="true"
              />
              {error}
            </p>
          ) : null}
        </div>

        <Button
          type="button"
          variant={isLoading ? "secondary" : "outline"}
          className="min-w-32"
          disabled={disabled || isLoading}
          onClick={onClick}
        >
          {isLoading ? (
            <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Icon className="size-4" aria-hidden="true" />
          )}
          {isLoading ? "Working..." : title}
        </Button>
      </div>
    </div>
  );
}
