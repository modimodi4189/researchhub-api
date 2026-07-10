"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileText,
  Lock,
  RefreshCw,
  Rows3,
  Unlock,
} from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { isApiError, type PaginationResponse, type PaperListItem } from "@/lib/api";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;

type LibraryState =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: PaginationResponse<PaperListItem>; error: null }
  | { status: "error"; data: null; error: string };

export function PaperLibrary() {
  const { apiRequest } = useAuth();
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LibraryState>({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    let isCurrent = true;

    async function loadPapers() {
      setState({ status: "loading", data: null, error: null });

      try {
        const data = await apiRequest<PaginationResponse<PaperListItem>>(
          "/api/v1/papers",
          {
            query: { page, limit: PAGE_SIZE },
          },
        );

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

    loadPapers();

    return () => {
      isCurrent = false;
    };
  }, [apiRequest, page, reloadKey]);

  const pagination = useMemo(() => {
    const data = state.status === "success" ? state.data : null;
    const total = data?.total ?? 0;
    const pages = data?.pages ?? 0;
    const first = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
    const last = data ? Math.min(page * data.limit, total) : 0;

    return { first, last, pages, total };
  }, [page, state]);

  const papers = state.status === "success" ? state.data.items : [];
  const isEmpty = state.status === "success" && papers.length === 0;

  return (
    <section
      id="library"
      aria-labelledby="paper-library-title"
      className="mx-auto flex max-w-7xl flex-col gap-4"
    >
      <div className="flex items-start justify-between gap-6 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <Rows3 className="size-4" aria-hidden="true" />
            Read-only library
          </div>
          <h1
            id="paper-library-title"
            className="mt-2 text-2xl font-semibold tracking-tight"
          >
            Paper Library
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Authenticated papers from the API, arranged for quick desktop
            scanning without editing or automation actions.
          </p>
        </div>

        <div className="flex min-w-44 flex-col items-end gap-2 text-right">
          <Badge variant="outline" className="h-7 rounded-md px-2.5">
            GET /api/v1/papers
          </Badge>
          <p className="text-xs text-muted-foreground">
            {state.status === "success"
              ? `${pagination.total} total papers`
              : "Loading authenticated data"}
          </p>
        </div>
      </div>

      {state.status === "loading" ? <PaperLibrarySkeleton /> : null}

      {state.status === "error" ? (
        <PaperLibraryError
          message={state.error}
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}

      {isEmpty ? <PaperLibraryEmpty /> : null}

      {state.status === "success" && papers.length > 0 ? (
        <>
          <div className="overflow-hidden rounded-md border border-border bg-card">
            <div className="grid grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px] items-center border-b border-border bg-muted/60 px-4 py-2.5 text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
              <span>Paper</span>
              <span>Visibility</span>
              <span>Category</span>
              <span>Updated</span>
              <span className="text-right">ID</span>
            </div>

            <div className="divide-y divide-border">
              {papers.map((paper) => (
                <PaperRow key={paper.id} paper={paper} />
              ))}
            </div>
          </div>

          <PaginationControls
            first={pagination.first}
            last={pagination.last}
            page={page}
            pages={pagination.pages}
            total={pagination.total}
            onPrevious={() => setPage((value) => Math.max(1, value - 1))}
            onNext={() =>
              setPage((value) => Math.min(pagination.pages, value + 1))
            }
          />
        </>
      ) : null}
    </section>
  );
}

function PaperRow({ paper }: { paper: PaperListItem }) {
  const preview = paper.abstract?.trim() || "No abstract provided.";
  const updatedAt = paper.updated_at ?? paper.created_at;
  const updatedLabel = formatDate(updatedAt);

  return (
    <article className="grid min-h-28 grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px] items-center gap-0 px-4 py-3 transition hover:bg-muted/35">
      <div className="min-w-0 pr-6">
        <div className="flex items-center gap-2">
          <FileText className="size-4 shrink-0 text-primary" aria-hidden="true" />
          <h2 className="truncate text-sm font-semibold text-foreground">
            {paper.title}
          </h2>
        </div>
        <p className="mt-2 line-clamp-2 max-w-4xl text-sm leading-5 text-muted-foreground">
          {preview}
        </p>
        <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
          <span>Created {formatDate(paper.created_at)}</span>
          <span aria-hidden="true">/</span>
          <span>{paper.summary ? "Summary available" : "No summary"}</span>
        </div>
      </div>

      <div>
        <Badge
          variant="secondary"
          className={cn(
            "h-7 rounded-md px-2.5",
            paper.is_public
              ? "bg-primary-subtle text-accent-foreground"
              : "bg-muted text-muted-foreground",
          )}
        >
          {paper.is_public ? (
            <Unlock className="size-3.5" aria-hidden="true" />
          ) : (
            <Lock className="size-3.5" aria-hidden="true" />
          )}
          {paper.is_public ? "Public" : "Private"}
        </Badge>
      </div>

      <div className="text-sm text-muted-foreground">
        {paper.category_id ? `#${paper.category_id}` : "Unassigned"}
      </div>

      <time className="text-sm text-muted-foreground" dateTime={updatedAt}>
        {updatedLabel}
      </time>

      <div className="text-right font-mono text-xs text-muted-foreground">
        {paper.id}
      </div>
    </article>
  );
}

function PaperLibrarySkeleton() {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-card">
      <div className="grid grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px] border-b border-border bg-muted/60 px-4 py-2.5">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="ml-auto h-4 w-8" />
      </div>

      <div className="divide-y divide-border">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={index}
            className="grid min-h-28 grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px] items-center px-4 py-3"
          >
            <div className="space-y-3 pr-6">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </div>
            <Skeleton className="h-7 w-20" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="ml-auto h-4 w-8" />
          </div>
        ))}
      </div>
    </div>
  );
}

function PaperLibraryEmpty() {
  return (
    <div className="flex min-h-80 items-center justify-center rounded-md border border-dashed border-border bg-card px-6 py-12 text-center">
      <div className="max-w-md">
        <div className="mx-auto flex size-12 items-center justify-center rounded-md bg-muted text-primary">
          <BookOpen className="size-6" aria-hidden="true" />
        </div>
        <h2 className="mt-4 text-base font-semibold">No papers yet</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          The authenticated request succeeded, but this account does not have
          papers to display on this page.
        </p>
      </div>
    </div>
  );
}

function PaperLibraryError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="rounded-md border border-destructive/30 bg-card px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex gap-3">
          <AlertCircle className="mt-0.5 size-5 shrink-0 text-destructive" />
          <div>
            <h2 className="text-sm font-semibold">Could not load papers</h2>
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
  );
}

function PaginationControls({
  first,
  last,
  onNext,
  onPrevious,
  page,
  pages,
  total,
}: {
  first: number;
  last: number;
  onNext: () => void;
  onPrevious: () => void;
  page: number;
  pages: number;
  total: number;
}) {
  const canGoPrevious = page > 1;
  const canGoNext = pages > 0 && page < pages;

  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-card px-4 py-3">
      <p className="text-sm text-muted-foreground">
        Showing{" "}
        <span className="font-medium text-foreground">
          {first}-{last}
        </span>{" "}
        of <span className="font-medium text-foreground">{total}</span>
      </p>
      <div className="flex items-center gap-3">
        <p className="min-w-24 text-center text-sm text-muted-foreground">
          Page <span className="font-medium text-foreground">{page}</span>
          <span> / </span>
          <span className="font-medium text-foreground">{Math.max(pages, 1)}</span>
        </p>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="Previous page"
            disabled={!canGoPrevious}
            onClick={onPrevious}
          >
            <ChevronLeft className="size-4" aria-hidden="true" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            aria-label="Next page"
            disabled={!canGoNext}
            onClick={onNext}
          >
            <ChevronRight className="size-4" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function getPaperLoadError(error: unknown) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again and reopen the library.";
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while requesting the paper library.";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}
