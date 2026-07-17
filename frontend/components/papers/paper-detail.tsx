"use client";

import type { ComponentType, ReactNode, SVGProps } from "react";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  BrainCircuit,
  CalendarDays,
  Edit3,
  FileText,
  Hash,
  Lock,
  RefreshCw,
  ScrollText,
  Tags,
  Trash2,
  Unlock,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/components/auth/auth-provider";
import {
  AiActionButton,
  type AiActionStatus,
} from "@/components/papers/ai-action-button";
import { ConfirmDeleteDialog } from "@/components/papers/confirm-delete-dialog";
import { PaperForm } from "@/components/papers/paper-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { isApiError, type Paper, type PaperMutationPayload } from "@/lib/api";
import { cn } from "@/lib/utils";

const SUMMARY_POLL_INTERVAL_MS = 3000;
const SUMMARY_POLL_ATTEMPTS = 120;

type DetailState =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: Paper; error: null }
  | { status: "error"; data: null; error: string };

type PaperAiAction = "summarize" | "classify";

type PaperAiActionState = {
  error: string | null;
  status: AiActionStatus;
};

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

  return (
    <PaperDetailContent
      paper={state.data}
      onPaperUpdated={(paper) =>
        setState({ status: "success", data: paper, error: null })
      }
    />
  );
}

function PaperDetailContent({
  onPaperUpdated,
  paper,
}: {
  onPaperUpdated: (paper: Paper) => void;
  paper: Paper;
}) {
  const { apiRequest } = useAuth();
  const router = useRouter();
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [aiActions, setAiActions] = useState<
    Record<PaperAiAction, PaperAiActionState>
  >({
    summarize: { status: "idle", error: null },
    classify: { status: "idle", error: null },
  });
  const updatedAt = paper.updated_at ?? paper.created_at;
  const isSummaryInProgress =
    paper.summary_status === "queued" || paper.summary_status === "processing";
  const dates = useMemo(
    () => [
      { label: "Created", value: paper.created_at },
      { label: "Updated", value: updatedAt },
    ],
    [paper.created_at, updatedAt],
  );

  async function submitPaperUpdate(payload: PaperMutationPayload) {
    return apiRequest<Paper>(`/api/v1/papers/${paper.id}`, {
      method: "PATCH",
      body: payload,
    });
  }

  function handlePaperSaved(nextPaper: Paper) {
    onPaperUpdated(nextPaper);
    setIsEditOpen(false);
    toast.success("Paper updated", {
      description: `${nextPaper.title} has been saved.`,
    });
  }

  async function handleAiAction(action: PaperAiAction) {
    if (action === "summarize") {
      await handleSummarizePaper();
      return;
    }

    const config = getPaperAiActionConfig(action);

    setAiActions((current) => ({
      ...current,
      [action]: { status: "loading", error: null },
    }));

    try {
      const updatedPaper = await apiRequest<Paper>(
        `/api/v1/papers/${paper.id}/${config.path}`,
        { method: "POST" },
      );
      onPaperUpdated(updatedPaper);

      const refreshedPaper = await apiRequest<Paper>(
        `/api/v1/papers/${paper.id}`,
      );
      onPaperUpdated(refreshedPaper);

      setAiActions((current) => ({
        ...current,
        [action]: { status: "success", error: null },
      }));
      toast.success(config.toastTitle, {
        description: config.toastDescription,
      });
    } catch (error) {
      const message = getPaperAiActionError(error, action);
      setAiActions((current) => ({
        ...current,
        [action]: { status: "error", error: message },
      }));
      toast.error(config.errorTitle, {
        description: message,
      });
    }
  }

  async function handleSummarizePaper() {
    const config = getPaperAiActionConfig("summarize");

    setAiActions((current) => ({
      ...current,
      summarize: { status: "loading", error: null },
    }));

    try {
      const queuedPaper = await apiRequest<Paper>(
        `/api/v1/papers/${paper.id}/${config.path}`,
        { method: "POST" },
      );
      onPaperUpdated(queuedPaper);

      const summarizedPaper = await waitForSummary();
      onPaperUpdated(summarizedPaper);

      setAiActions((current) => ({
        ...current,
        summarize: { status: "success", error: null },
      }));
      toast.success(config.toastTitle, {
        description: config.toastDescription,
      });
    } catch (error) {
      const message = getPaperAiActionError(error, "summarize");
      setAiActions((current) => ({
        ...current,
        summarize: { status: "error", error: message },
      }));
      toast.error(config.errorTitle, {
        description: message,
      });
    }
  }

  async function waitForSummary() {
    for (let attempt = 0; attempt < SUMMARY_POLL_ATTEMPTS; attempt += 1) {
      await sleep(SUMMARY_POLL_INTERVAL_MS);

      const nextPaper = await apiRequest<Paper>(`/api/v1/papers/${paper.id}`);
      onPaperUpdated(nextPaper);

      if (nextPaper.summary_status === "complete") {
        return nextPaper;
      }

      if (nextPaper.summary_status === "failed") {
        throw new Error(
          nextPaper.summary_error ||
            "Summary generation failed in the background worker.",
        );
      }
    }

    throw new Error(
      "Summary generation is still processing. Refresh this paper in a few minutes.",
    );
  }

  async function handlePaperDeleted() {
    setIsDeleting(true);
    setDeleteError(null);

    try {
      await apiRequest<void>(`/api/v1/papers/${paper.id}`, {
        method: "DELETE",
        responseType: "void",
      });
      toast.success("Paper deleted", {
        description: `${paper.title} was removed from your library.`,
      });
      router.push("/app");
    } catch (error) {
      const message = getPaperDeleteError(error);
      setDeleteError(message);
      toast.error("Could not delete paper", {
        description: message,
      });
      throw error;
    } finally {
      setIsDeleting(false);
    }
  }

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
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="h-7 rounded-md px-2.5">
                GET /api/v1/papers/{paper.id}
              </Badge>
              <Button
                type="button"
                variant="outline"
                className="text-muted-foreground hover:border-destructive/40 hover:bg-destructive/10 hover:text-destructive"
                onClick={() => setIsDeleteOpen(true)}
              >
                <Trash2 className="size-4" aria-hidden="true" />
                Delete
              </Button>
              <Button type="button" onClick={() => setIsEditOpen(true)}>
                <Edit3 className="size-4" aria-hidden="true" />
                Edit
              </Button>
            </div>
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

        <section className="mt-5">
          <div className="mb-3 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold">AI Actions</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Backend AI operations with paper refresh on completion.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <AiActionButton
              description="Generate a saved summary from the paper content."
              endpointLabel="POST /summarize"
              error={aiActions.summarize.error}
              icon={BrainCircuit}
              loadingLabel="Summary queued. This can take several minutes the first time..."
              status={
                isSummaryInProgress ? "loading" : aiActions.summarize.status
              }
              successMessage="Summary generated and paper refreshed."
              title="Summarize"
              disabled={isAnyAiActionLoading(aiActions) || isSummaryInProgress}
              onClick={() => handleAiAction("summarize")}
            />
            <AiActionButton
              description="Classify the paper and assign the matching category."
              endpointLabel="POST /classify"
              error={aiActions.classify.error}
              icon={Tags}
              loadingLabel="Classifying paper and refreshing this paper..."
              status={aiActions.classify.status}
              successMessage="Classification saved and paper refreshed."
              title="Classify"
              disabled={isAnyAiActionLoading(aiActions)}
              onClick={() => handleAiAction("classify")}
            />
          </div>
        </section>
      </div>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-h-[calc(100vh-4rem)] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>Edit Paper</DialogTitle>
            <DialogDescription>
              Save changes through PATCH /api/v1/papers/{paper.id}.
            </DialogDescription>
          </DialogHeader>
          <PaperForm
            initialPaper={paper}
            cancelLabel="Cancel"
            saveLabel="Save changes"
            submitPaper={submitPaperUpdate}
            onCancel={() => setIsEditOpen(false)}
            onSaved={handlePaperSaved}
          />
        </DialogContent>
      </Dialog>

      <ConfirmDeleteDialog
        error={deleteError}
        isDeleting={isDeleting}
        open={isDeleteOpen}
        paperTitle={paper.title}
        onConfirm={handlePaperDeleted}
        onOpenChange={setIsDeleteOpen}
      />

      <div className="grid grid-cols-[minmax(0,0.9fr)_minmax(520px,1.4fr)] gap-5">
        <div className="flex min-w-0 flex-col gap-5">
          <ReaderSection title="Abstract">
            <ReadableText value={paper.abstract} empty="No abstract provided." />
          </ReaderSection>

          <ReaderSection title="Summary">
            <SummaryStatus paper={paper} />
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

function getPaperDeleteError(error: unknown) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again before deleting this paper.";
    }

    if (error.status === 403) {
      return "You are not authorized to delete this paper.";
    }

    if (error.status === 404) {
      return "The API could not find this paper. It may already be deleted.";
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while deleting the paper.";
}

function getPaperAiActionConfig(action: PaperAiAction) {
  if (action === "summarize") {
    return {
      errorTitle: "Could not summarize paper",
      path: "summarize",
      toastDescription: "The detail view has been refreshed with the latest paper data.",
      toastTitle: "Summary generated",
    };
  }

  return {
    errorTitle: "Could not classify paper",
    path: "classify",
    toastDescription: "The detail view has been refreshed with the latest paper data.",
    toastTitle: "Paper classified",
  };
}

function getPaperAiActionError(error: unknown, action: PaperAiAction) {
  const actionLabel = action === "summarize" ? "summarizing" : "classifying";

  if (isApiError(error)) {
    if (error.status === 401) {
      return `Your session could not be verified. Log in again before ${actionLabel} this paper.`;
    }

    if (error.status === 403) {
      return `You are not authorized to ${action} this paper.`;
    }

    if (error.status === 404) {
      return "The API could not find this paper.";
    }

    if (error.status === 422) {
      return error.message;
    }

    if (error.status === 503) {
      return `The AI service could not finish ${actionLabel} this paper. Try again in a moment.`;
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return `An unknown error occurred while ${actionLabel} the paper.`;
}

function SummaryStatus({ paper }: { paper: Paper }) {
  if (paper.summary_status === "idle" && !paper.summary_error) {
    return null;
  }

  const statusLabel = getSummaryStatusLabel(paper);

  return (
    <div
      className={cn(
        "mb-3 rounded-md border px-3 py-2 text-sm",
        paper.summary_status === "failed"
          ? "border-destructive/30 bg-destructive/5 text-destructive"
          : "border-border bg-muted/50 text-muted-foreground",
      )}
    >
      <span className="font-medium">{statusLabel}</span>
      {paper.summary_error ? <span> {paper.summary_error}</span> : null}
    </div>
  );
}

function getSummaryStatusLabel(paper: Paper) {
  if (paper.summary_status === "queued") {
    return "Summary queued.";
  }

  if (paper.summary_status === "processing") {
    return "Summary processing.";
  }

  if (paper.summary_status === "complete") {
    return "Summary complete.";
  }

  if (paper.summary_status === "failed") {
    return "Summary failed.";
  }

  return `Summary status: ${paper.summary_status}.`;
}

function isAnyAiActionLoading(
  actions: Record<PaperAiAction, PaperAiActionState>,
) {
  return Object.values(actions).some((action) => action.status === "loading");
}

function sleep(durationMs: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, durationMs);
  });
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}
