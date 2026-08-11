"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowUpRight,
  FileSearch,
  Lock,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Unlock,
} from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  isApiError,
  type PaginationResponse,
  type PaperListItem,
  type SearchScope,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const LIMIT_OPTIONS = [5, 10, 15, 20] as const;

type SearchState =
  | { status: "idle"; data: null; error: null }
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: PaginationResponse<PaperListItem>; error: null }
  | { status: "error"; data: null; error: string };

export function SemanticSearch() {
  const { apiRequest } = useAuth();
  const [draftQuery, setDraftQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [scope, setScope] = useState<SearchScope>("my");
  const [limit, setLimit] = useState(5);
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<SearchState>({
    status: "idle",
    data: null,
    error: null,
  });

  useEffect(() => {
    const query = submittedQuery.trim();

    if (!query) {
      return;
    }

    let isCurrent = true;

    async function runSearch() {
      setState({ status: "loading", data: null, error: null });

      try {
        const data = await apiRequest<PaginationResponse<PaperListItem>>(
          `/api/v1/search/${scope}`,
          {
            query: { q: query, k: limit },
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
          error: getSearchError(error, scope),
        });
      }
    }

    runSearch();

    return () => {
      isCurrent = false;
    };
  }, [apiRequest, limit, reloadKey, scope, submittedQuery]);

  const results = state.status === "success" ? state.data.items : [];
  const isEmpty = state.status === "success" && results.length === 0;
  const activeEndpoint =
    scope === "my" ? "GET /api/v1/search/my" : "GET /api/v1/search/public";

  const resultSummary = useMemo(() => {
    if (state.status === "idle") {
      return "Enter a search phrase to query indexed papers.";
    }

    if (state.status === "loading") {
      return "Searching semantic index";
    }

    if (state.status === "success") {
      return `${state.data.total} result${state.data.total === 1 ? "" : "s"} for "${submittedQuery}"`;
    }

    return "Search request failed";
  }, [state, submittedQuery]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = draftQuery.trim();

    if (!nextQuery) {
      setSubmittedQuery("");
      setState({ status: "idle", data: null, error: null });
      return;
    }

    setSubmittedQuery(nextQuery);
  }

  return (
    <section
      id="semantic-search"
      aria-labelledby="semantic-search-title"
      className="mx-auto flex max-w-7xl flex-col gap-4"
    >
      <div className="flex items-start justify-between gap-6 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <FileSearch className="size-4" aria-hidden="true" />
            Semantic search
          </div>
          <h1
            id="semantic-search-title"
            className="mt-2 text-2xl font-semibold tracking-tight"
          >
            Search Papers
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Query your private index or public papers and open a matching paper
            directly from the result list.
          </p>
        </div>

        <div className="flex min-w-56 flex-col items-end gap-2 text-right">
          <Badge variant="outline" className="h-7 rounded-md px-2.5">
            {activeEndpoint}
          </Badge>
          <p className="text-xs text-muted-foreground">{resultSummary}</p>
        </div>
      </div>

      <div className="rounded-md border border-border bg-card px-4 py-4">
        <form
          className="grid grid-cols-[1fr_176px_124px] items-end gap-3"
          onSubmit={handleSubmit}
        >
          <label className="min-w-0">
            <span className="mb-2 block text-xs font-medium text-muted-foreground">
              Search query
            </span>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                className="h-9 pl-8"
                placeholder="Try a concept, method, or paper topic"
                value={draftQuery}
                onChange={(event) => setDraftQuery(event.target.value)}
              />
            </div>
          </label>

          <label>
            <span className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <SlidersHorizontal className="size-3.5" aria-hidden="true" />
              Result limit
            </span>
            <select
              className="h-9 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
            >
              {LIMIT_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option} results
                </option>
              ))}
            </select>
          </label>

          <Button type="submit" className="h-9" disabled={!draftQuery.trim()}>
            <Search className="size-4" aria-hidden="true" />
            Search
          </Button>
        </form>

        <div
          role="tablist"
          className="mt-4 inline-flex rounded-md border border-border bg-muted/50 p-1"
          aria-label="Search scope"
        >
          <ScopeButton
            active={scope === "my"}
            label="My Papers"
            onClick={() => setScope("my")}
          />
          <ScopeButton
            active={scope === "public"}
            label="Public"
            onClick={() => setScope("public")}
          />
        </div>
      </div>

      {state.status === "idle" ? <SearchIdle /> : null}
      {state.status === "loading" ? <SearchSkeleton /> : null}
      {state.status === "error" ? (
        <SearchError
          message={state.error}
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}
      {isEmpty ? (
        <SearchEmpty query={submittedQuery} scope={scope} limit={limit} />
      ) : null}
      {state.status === "success" && results.length > 0 ? (
        <SearchResults results={results} />
      ) : null}
    </section>
  );
}

function ScopeButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={cn(
        "h-8 min-w-28 rounded px-3 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/40",
        active
          ? "bg-background text-foreground shadow-sm"
          : "text-muted-foreground hover:text-foreground",
      )}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function SearchResults({ results }: { results: PaperListItem[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-card">
      <div className="grid grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px_44px] items-center border-b border-border bg-muted/60 px-4 py-2.5 text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
        <span>Result</span>
        <span>Visibility</span>
        <span>Category</span>
        <span>Updated</span>
        <span className="text-right">ID</span>
        <span className="sr-only">Open</span>
      </div>

      <div className="divide-y divide-border">
        {results.map((paper) => (
          <ResultRow key={paper.id} paper={paper} />
        ))}
      </div>
    </div>
  );
}

function ResultRow({ paper }: { paper: PaperListItem }) {
  const preview = paper.abstract?.trim() || "No abstract provided.";
  const updatedAt = paper.updated_at ?? paper.created_at;

  return (
    <Link
      href={`/app/papers/${paper.id}`}
      className="grid min-h-28 grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px_44px] items-center px-4 py-3 transition hover:bg-muted/35 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/40"
    >
      <div className="min-w-0 pr-6">
        <div className="flex items-center gap-2">
          <FileSearch
            className="size-4 shrink-0 text-primary"
            aria-hidden="true"
          />
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
        {paper.category?.name ??
          (paper.category_id ? `#${paper.category_id}` : "Unassigned")}
      </div>

      <time className="text-sm text-muted-foreground" dateTime={updatedAt}>
        {formatDate(updatedAt)}
      </time>

      <div className="text-right font-mono text-xs text-muted-foreground">
        {paper.id}
      </div>

      <div className="flex justify-end text-muted-foreground">
        <ArrowUpRight className="size-4" aria-hidden="true" />
      </div>
    </Link>
  );
}

function SearchIdle() {
  return (
    <div className="flex min-h-72 items-center justify-center rounded-md border border-dashed border-border bg-card px-6 py-12 text-center">
      <div className="max-w-md">
        <div className="mx-auto flex size-12 items-center justify-center rounded-md bg-muted text-primary">
          <FileSearch className="size-6" aria-hidden="true" />
        </div>
        <h2 className="mt-4 text-base font-semibold">Ready to search</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Submit a phrase to run semantic search against your papers or the
          public index.
        </p>
      </div>
    </div>
  );
}

function SearchSkeleton() {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-card">
      <div className="grid grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px_44px] border-b border-border bg-muted/60 px-4 py-2.5">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
        <Skeleton className="ml-auto h-4 w-8" />
        <Skeleton className="ml-auto size-8" />
      </div>

      <div className="divide-y divide-border">
        {Array.from({ length: 5 }).map((_, index) => (
          <div
            key={index}
            className="grid min-h-28 grid-cols-[minmax(420px,1fr)_120px_126px_130px_96px_44px] items-center px-4 py-3"
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
            <Skeleton className="ml-auto size-8" />
          </div>
        ))}
      </div>
    </div>
  );
}

function SearchEmpty({
  limit,
  query,
  scope,
}: {
  limit: number;
  query: string;
  scope: SearchScope;
}) {
  const scopeLabel = scope === "my" ? "your papers" : "public papers";

  return (
    <div className="flex min-h-72 items-center justify-center rounded-md border border-dashed border-border bg-card px-6 py-12 text-center">
      <div className="max-w-md">
        <div className="mx-auto flex size-12 items-center justify-center rounded-md bg-muted text-primary">
          <Search className="size-6" aria-hidden="true" />
        </div>
        <h2 className="mt-4 text-base font-semibold">No matches found</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          The API returned no {scopeLabel} for &quot;{query}&quot; with a limit
          of {limit}.
        </p>
      </div>
    </div>
  );
}

function SearchError({
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
            <h2 className="text-sm font-semibold">Could not run search</h2>
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

function getSearchError(error: unknown, scope: SearchScope) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again and reopen search.";
    }

    return `The ${scope} search endpoint returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while requesting semantic search.";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}
