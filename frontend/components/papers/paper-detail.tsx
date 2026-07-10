"use client";

import type { ComponentType, ReactNode, SVGProps } from "react";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  FileText,
  Hash,
  Lock,
  RefreshCw,
  ScrollText,
  Unlock,
} from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { isApiError, type Paper } from "@/lib/api";
import { cn } from "@/lib/utils";

type DetailState =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: Paper; error: null }
  | { status: "error"; data: null; error: string };

export function PaperDetail({ paperId }: { paperId: string }) {
  const { apiRequest } = useAuth();
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<DetailState>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    let isCurrent = true;

    async function loadPaper() {
      setState({ status: "loading", data: null, error: null });

      try {
        const data = await apiRequest<Paper>(`/api/v1/papers/${paperId}`);

        if (isCurrent) {
          setState({ status: "success", data, error: null });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        setState({
          status: "error",
          data: null,
          error: getPaperLoadError(error),
        });
      }
    }

    loadPaper();

    return () => {
      isCurrent = false;
    };
  }, [apiRequest, paperId, reloadKey]);

  if (state.status === "loading") {
    return <PaperDetailSkeleton />;
  }

  if (state.status === "error") {
    return (
      <PaperDetailError
        message={state.error}
        onRetry={() => setReloadKey((value) => value + 1)}
      />
    );
  }

  return <PaperDetailContent paper={state.data} />;
}

function PaperDetailContent({ paper }: { paper: Paper }) {
  const updatedAt = paper.updated_at ?? paper.created_at;
  const dates = useMemo(
    () => [
      { label: "Created", value: paper.created_at },
      { label: "Updated", value: updatedAt },
    ],
    [paper.created_at, updatedAt],
  );

  return (
    <article className="mx-auto flex max-w-7xl flex-col gap-5">
      <div className="border-b border-border pb-5">
        <Button asChild variant="ghost" className="-ml-2 mb-4">
          <Link href="/app">
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to Library
          </Link>
        </Button>

        <div className="flex items-start justify-between gap-8">
          <div className="min-w-0">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
              <FileText className="size-4" aria-hidden="true" />
              Paper Detail
            </div>
            <h1 className="mt-2 max-w-5xl text-3xl font-semibold leading-tight tracking-tight">
              {paper.title}
            </h1>
          </div>

          <div className="flex min-w-52 flex-col items-end gap-2 text-right">
            <Badge variant="outline" className="h-7 rounded-md px-2.5">
              GET /api/v1/papers/{paper.id}
            </Badge>
            <p className="font-mono text-xs text-muted-foreground">
              Paper #{paper.id}
            </p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-[160px_160px_160px_1fr] gap-3">
          <MetaTile
            icon={paper.is_public ? Unlock : Lock}
            label="Visibility"
            value={paper.is_public ? "Public" : "Private"}
            emphasized={paper.is_public}
          />
          <MetaTile
            icon={Hash}
            label="Category"
            value={paper.category_id ? `#${paper.category_id}` : "Unassigned"}
          />
          {dates.map((date) => (
            <MetaTile
              key={date.label}
              icon={CalendarDays}
              label={date.label}
              value={formatDate(date.value)}
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,0.9fr)_minmax(520px,1.4fr)] gap-5">
        <div className="flex min-w-0 flex-col gap-5">
          <ReaderSection title="Abstract">
            <ReadableText value={paper.abstract} empty="No abstract provided." />
          </ReaderSection>

          <ReaderSection title="Summary">
            <ReadableText value={paper.summary} empty="No summary available." />
          </ReaderSection>
        </div>

        <ReaderSection
          title="Content Viewer"
          action={
            <Badge variant="secondary" className="h-7 rounded-md px-2.5">
              <ScrollText className="size-3.5" aria-hidden="true" />
              Read only
            </Badge>
          }
        >
          <div className="max-h-[calc(100vh-18rem)] min-h-[32rem] overflow-auto rounded-md border border-border bg-background px-5 py-4">
            <ReadableText
              value={paper.content}
              empty="No full content is stored for this paper."
              className="text-[0.93rem] leading-7"
            />
          </div>
        </ReaderSection>
      </div>
    </article>
  );
}

function ReaderSection({
  action,
  children,
  title,
}: {
  action?: ReactNode;
  children: ReactNode;
  title: string;
}) {
  return (
    <section className="rounded-md border border-border bg-card">
      <div className="flex min-h-12 items-center justify-between gap-4 border-b border-border px-4">
        <h2 className="text-sm font-semibold">{title}</h2>
        {action}
      </div>
      <div className="px-4 py-4">{children}</div>
    </section>
  );
}

function ReadableText({
  className,
  empty,
  value,
}: {
  className?: string;
  empty: string;
  value: string | null;
}) {
  const text = value?.trim();

  if (!text) {
    return <p className="text-sm leading-6 text-muted-foreground">{empty}</p>;
  }

  return (
    <p className={cn("whitespace-pre-wrap text-sm leading-6", className)}>
      {text}
    </p>
  );
}

function MetaTile({
  emphasized,
  icon: Icon,
  label,
  value,
}: {
  emphasized?: boolean;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2.5">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="size-3.5" aria-hidden="true" />
        {label}
      </div>
      <p
        className={cn(
          "mt-1 text-sm font-medium",
          emphasized ? "text-accent-foreground" : "text-foreground",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function PaperDetailSkeleton() {
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      <div className="border-b border-border pb-5">
        <Skeleton className="mb-4 h-8 w-36" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="mt-3 h-9 w-3/5" />
        <div className="mt-5 grid grid-cols-[160px_160px_160px_1fr] gap-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-16 rounded-md" />
          ))}
        </div>
      </div>
      <div className="grid grid-cols-[minmax(0,0.9fr)_minmax(520px,1.4fr)] gap-5">
        <div className="space-y-5">
          <Skeleton className="h-48 rounded-md" />
          <Skeleton className="h-56 rounded-md" />
        </div>
        <Skeleton className="h-[36rem] rounded-md" />
      </div>
    </div>
  );
}

function PaperDetailError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="mx-auto max-w-7xl">
      <Button asChild variant="ghost" className="-ml-2 mb-4">
        <Link href="/app">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Back to Library
        </Link>
      </Button>
      <div className="rounded-md border border-destructive/30 bg-card px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex gap-3">
            <AlertCircle className="mt-0.5 size-5 shrink-0 text-destructive" />
            <div>
              <h2 className="text-sm font-semibold">Could not load paper</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                {message}
              </p>
            </div>
          </div>
          <Button type="button" variant="outline" onClick={onRetry}>
            <RefreshCw className="size-4" aria-hidden="true" />
            Retry
          </Button>
        </div>
      </div>
    </div>
  );
}

function getPaperLoadError(error: unknown) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again and reopen the paper.";
    }

    if (error.status === 404) {
      return "The API could not find this paper.";
    }

    if (error.status === 403) {
      return "You are not authorized to view this paper.";
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while requesting the paper.";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}
