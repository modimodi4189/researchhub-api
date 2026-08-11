"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Check,
  Edit3,
  FilePlus2,
  FileText,
  FolderKanban,
  Loader2,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/components/auth/auth-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  isApiError,
  type Collection,
  type CollectionMutationPayload,
  type CollectionWithPapers,
  type PaginationResponse,
  type PaperListItem,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const COLLECTION_PAGE_SIZE = 50;
const PAPER_PICKER_LIMIT = 100;
const COLLECTION_NAME_MAX_LENGTH = 255;

type CollectionsState =
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: PaginationResponse<Collection>; error: null }
  | { status: "error"; data: null; error: string };

type DetailState =
  | { status: "idle"; data: null; error: null }
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: CollectionWithPapers; error: null }
  | { status: "error"; data: null; error: string };

type PapersState =
  | { status: "idle"; data: null; error: null }
  | { status: "loading"; data: null; error: null }
  | { status: "success"; data: PaperListItem[]; error: null }
  | { status: "error"; data: null; error: string };

export function CollectionsManager() {
  const { apiRequest } = useAuth();
  const [collectionsState, setCollectionsState] = useState<CollectionsState>({
    status: "loading",
    data: null,
    error: null,
  });
  const [detailState, setDetailState] = useState<DetailState>({
    status: "idle",
    data: null,
    error: null,
  });
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(
    null,
  );
  const [reloadKey, setReloadKey] = useState(0);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [renamingCollection, setRenamingCollection] =
    useState<Collection | null>(null);
  const [deletingCollection, setDeletingCollection] =
    useState<Collection | null>(null);
  const [isAddPaperOpen, setIsAddPaperOpen] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    async function loadCollections() {
      setCollectionsState({ status: "loading", data: null, error: null });

      try {
        const data = await apiRequest<PaginationResponse<Collection>>(
          "/api/v1/collections",
          { query: { page: 1, limit: COLLECTION_PAGE_SIZE } },
        );

        if (!isCurrent) {
          return;
        }

        setCollectionsState({ status: "success", data, error: null });

        setSelectedCollectionId((currentId) => {
          if (data.items.some((collection) => collection.id === currentId)) {
            return currentId;
          }

          return data.items[0]?.id ?? null;
        });
      } catch (error) {
        if (isCurrent) {
          setCollectionsState({
            status: "error",
            data: null,
            error: getCollectionLoadError(error),
          });
        }
      }
    }

    loadCollections();

    return () => {
      isCurrent = false;
    };
  }, [apiRequest, reloadKey]);

  useEffect(() => {
    if (!selectedCollectionId) {
      return;
    }

    let isCurrent = true;

    async function loadCollectionDetail() {
      setDetailState({ status: "loading", data: null, error: null });

      try {
        const data = await apiRequest<CollectionWithPapers>(
          `/api/v1/collections/${selectedCollectionId}`,
        );

        if (isCurrent) {
          setDetailState({ status: "success", data, error: null });
        }
      } catch (error) {
        if (isCurrent) {
          setDetailState({
            status: "error",
            data: null,
            error: getCollectionLoadError(error),
          });
        }
      }
    }

    loadCollectionDetail();

    return () => {
      isCurrent = false;
    };
  }, [apiRequest, selectedCollectionId]);

  const collections =
    collectionsState.status === "success" ? collectionsState.data.items : [];
  const selectedCollection =
    detailState.status === "success" ? detailState.data : null;
  const totalCollections =
    collectionsState.status === "success" ? collectionsState.data.total : 0;

  async function submitCollection(payload: CollectionMutationPayload) {
    return apiRequest<Collection>("/api/v1/collections", {
      method: "POST",
      body: payload,
    });
  }

  async function submitRename(payload: CollectionMutationPayload) {
    if (!renamingCollection) {
      throw new Error("No collection selected for rename.");
    }

    return apiRequest<Collection>(`/api/v1/collections/${renamingCollection.id}`, {
      method: "PATCH",
      body: payload,
    });
  }

  function handleCollectionCreated(collection: Collection) {
    setIsCreateOpen(false);
    upsertCollection(collection);
    setSelectedCollectionId(collection.id);
    toast.success("Collection created", {
      description: `${collection.name} is ready for papers.`,
    });
  }

  function handleCollectionRenamed(collection: Collection) {
    setRenamingCollection(null);
    upsertCollection(collection);
    setDetailState((current) => {
      if (current.status !== "success" || current.data.id !== collection.id) {
        return current;
      }

      return {
        status: "success",
        data: { ...current.data, ...collection },
        error: null,
      };
    });
    toast.success("Collection renamed", {
      description: `${collection.name} has been saved.`,
    });
  }

  async function handleCollectionDeleted(collection: Collection) {
    await apiRequest<void>(`/api/v1/collections/${collection.id}`, {
      method: "DELETE",
      responseType: "void",
    });

    const nextCollections = collections.filter((item) => item.id !== collection.id);
    setCollectionsState((current) => {
      if (current.status !== "success") {
        return current;
      }

      return {
        status: "success",
        data: {
          ...current.data,
          items: nextCollections,
          total: Math.max(0, current.data.total - 1),
          pages: Math.ceil(
            Math.max(0, current.data.total - 1) / current.data.limit,
          ),
        },
        error: null,
      };
    });
      setDeletingCollection(null);
      setSelectedCollectionId(nextCollections[0]?.id ?? null);
      if (nextCollections.length === 0) {
        setDetailState({ status: "idle", data: null, error: null });
      }
      toast.success("Collection deleted", {
      description: `${collection.name} was removed.`,
    });
  }

  function upsertCollection(collection: Collection) {
    setCollectionsState((current) => {
      if (current.status !== "success") {
        return current;
      }

      const existingIndex = current.data.items.findIndex(
        (item) => item.id === collection.id,
      );
      const nextItems =
        existingIndex >= 0
          ? current.data.items.map((item) =>
              item.id === collection.id ? collection : item,
            )
          : [collection, ...current.data.items];

      return {
        status: "success",
        data: {
          ...current.data,
          items: nextItems,
          total:
            existingIndex >= 0 ? current.data.total : current.data.total + 1,
          pages:
            existingIndex >= 0
              ? current.data.pages
              : Math.ceil((current.data.total + 1) / current.data.limit),
        },
        error: null,
      };
    });
  }

  async function refreshSelectedCollection() {
    if (!selectedCollectionId) {
      return;
    }

    const data = await apiRequest<CollectionWithPapers>(
      `/api/v1/collections/${selectedCollectionId}`,
    );
    setDetailState({ status: "success", data, error: null });
  }

  return (
    <section
      id="collections"
      aria-labelledby="collections-title"
      className="mx-auto flex max-w-7xl flex-col gap-4"
    >
      <div className="flex items-start justify-between gap-6 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <FolderKanban className="size-4" aria-hidden="true" />
            Collection workspace
          </div>
          <h1
            id="collections-title"
            className="mt-2 text-2xl font-semibold tracking-tight"
          >
            Collections
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            Organize library papers into named sets, then add or remove papers
            from the selected collection.
          </p>
        </div>

        <div className="flex min-w-56 flex-col items-end gap-2 text-right">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="h-7 rounded-md px-2.5">
              GET /api/v1/collections
            </Badge>
            <Button type="button" onClick={() => setIsCreateOpen(true)}>
              <Plus className="size-4" aria-hidden="true" />
              New Collection
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            {collectionsState.status === "success"
              ? `${totalCollections} total collections`
              : "Loading authenticated data"}
          </p>
        </div>
      </div>

      <CollectionFormDialog
        key={isCreateOpen ? "create-open" : "create-closed"}
        open={isCreateOpen}
        title="Create Collection"
        description="Create a collection through POST /api/v1/collections."
        saveLabel="Create collection"
        submitCollection={submitCollection}
        onOpenChange={setIsCreateOpen}
        onSaved={handleCollectionCreated}
      />

      <CollectionFormDialog
        key={renamingCollection?.id ?? "rename-closed"}
        open={Boolean(renamingCollection)}
        initialName={renamingCollection?.name}
        title="Rename Collection"
        description="Save the new name through PATCH /api/v1/collections/{id}."
        saveLabel="Save name"
        submitCollection={submitRename}
        onOpenChange={(open) => {
          if (!open) {
            setRenamingCollection(null);
          }
        }}
        onSaved={handleCollectionRenamed}
      />

      {deletingCollection ? (
        <DeleteCollectionDialog
          collection={deletingCollection}
          open={Boolean(deletingCollection)}
          onDelete={handleCollectionDeleted}
          onOpenChange={(open) => {
            if (!open) {
              setDeletingCollection(null);
            }
          }}
        />
      ) : null}

      {selectedCollection ? (
        <AddPaperDialog
          collection={selectedCollection}
          open={isAddPaperOpen}
          onCollectionUpdated={refreshSelectedCollection}
          onOpenChange={setIsAddPaperOpen}
        />
      ) : null}

      {collectionsState.status === "loading" ? <CollectionsSkeleton /> : null}

      {collectionsState.status === "error" ? (
        <CollectionsError
          message={collectionsState.error}
          title="Could not load collections"
          onRetry={() => setReloadKey((value) => value + 1)}
        />
      ) : null}

      {collectionsState.status === "success" && collections.length === 0 ? (
        <CollectionsEmpty onCreate={() => setIsCreateOpen(true)} />
      ) : null}

      {collectionsState.status === "success" && collections.length > 0 ? (
        <div className="grid min-h-[calc(100vh-13.5rem)] grid-cols-[360px_minmax(0,1fr)] overflow-hidden rounded-md border border-border bg-card">
          <CollectionList
            collections={collections}
            selectedCollectionId={selectedCollectionId}
            onCreate={() => setIsCreateOpen(true)}
            onDelete={setDeletingCollection}
            onRename={setRenamingCollection}
            onSelect={setSelectedCollectionId}
          />

          <CollectionDetail
            state={detailState}
            onAddPaper={() => setIsAddPaperOpen(true)}
            onRemovePaper={async (paper) => {
              if (!selectedCollection) {
                return;
              }

              await apiRequest<void>(
                `/api/v1/collections/${selectedCollection.id}/papers/${paper.id}`,
                { method: "DELETE", responseType: "void" },
              );
              await refreshSelectedCollection();
              toast.success("Paper removed", {
                description: `${paper.title} was removed from ${selectedCollection.name}.`,
              });
            }}
            onRetry={refreshSelectedCollection}
          />
        </div>
      ) : null}
    </section>
  );
}

function CollectionList({
  collections,
  onCreate,
  onDelete,
  onRename,
  onSelect,
  selectedCollectionId,
}: {
  collections: Collection[];
  onCreate: () => void;
  onDelete: (collection: Collection) => void;
  onRename: (collection: Collection) => void;
  onSelect: (collectionId: number) => void;
  selectedCollectionId: number | null;
}) {
  return (
    <aside className="border-r border-border bg-surface/70">
      <div className="flex h-12 items-center justify-between border-b border-border px-4">
        <h2 className="text-sm font-semibold">Collection List</h2>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Create collection"
          onClick={onCreate}
        >
          <Plus className="size-4" aria-hidden="true" />
        </Button>
      </div>
      <div className="max-h-[calc(100vh-16.5rem)] overflow-auto">
        {collections.map((collection) => (
          <div
            key={collection.id}
            className={cn(
              "grid min-h-16 grid-cols-[1fr_36px] items-center border-b border-border px-3 transition",
              collection.id === selectedCollectionId
                ? "bg-primary-subtle/70"
                : "hover:bg-muted/50",
            )}
          >
            <button
              type="button"
              className="min-w-0 rounded-sm py-3 text-left focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/40"
              onClick={() => onSelect(collection.id)}
            >
              <span className="block truncate text-sm font-medium">
                {collection.name}
              </span>
              <span className="mt-1 block text-xs text-muted-foreground">
                Updated {formatDate(collection.updated_at ?? collection.created_at)}
              </span>
            </button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Actions for ${collection.name}`}
                >
                  <MoreHorizontal className="size-4" aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-40">
                <DropdownMenuItem
                  onSelect={(event) => {
                    event.preventDefault();
                    onRename(collection);
                  }}
                >
                  <Edit3 className="size-4" aria-hidden="true" />
                  Rename
                </DropdownMenuItem>
                <DropdownMenuItem
                  variant="destructive"
                  onSelect={(event) => {
                    event.preventDefault();
                    onDelete(collection);
                  }}
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ))}
      </div>
    </aside>
  );
}

function CollectionDetail({
  onAddPaper,
  onRemovePaper,
  onRetry,
  state,
}: {
  onAddPaper: () => void;
  onRemovePaper: (paper: PaperListItem) => Promise<void>;
  onRetry: () => void;
  state: DetailState;
}) {
  if (state.status === "idle") {
    return (
      <div className="flex items-center justify-center p-6 text-sm text-muted-foreground">
        Select a collection to view its papers.
      </div>
    );
  }

  if (state.status === "loading") {
    return <CollectionDetailSkeleton />;
  }

  if (state.status === "error") {
    return (
      <div className="p-5">
        <CollectionsError
          message={state.error}
          title="Could not load collection"
          onRetry={onRetry}
        />
      </div>
    );
  }

  const collection = state.data;
  const papers = collection.papers ?? [];

  return (
    <section className="flex min-w-0 flex-col">
      <div className="flex min-h-24 items-start justify-between gap-6 border-b border-border px-5 py-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <FolderKanban className="size-4" aria-hidden="true" />
            Collection Detail
          </div>
          <h2 className="mt-2 truncate text-2xl font-semibold tracking-tight">
            {collection.name}
          </h2>
          <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
            <span>Created {formatDate(collection.created_at)}</span>
            <span aria-hidden="true">/</span>
            <span>{papers.length} papers</span>
            <span aria-hidden="true">/</span>
            <span className="font-mono">#{collection.id}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-7 rounded-md px-2.5">
            GET /api/v1/collections/{collection.id}
          </Badge>
          <Button type="button" onClick={onAddPaper}>
            <FilePlus2 className="size-4" aria-hidden="true" />
            Add Paper
          </Button>
        </div>
      </div>

      {papers.length === 0 ? (
        <div className="flex flex-1 items-center justify-center px-6 py-12 text-center">
          <div className="max-w-md">
            <div className="mx-auto flex size-12 items-center justify-center rounded-md bg-muted text-primary">
              <FileText className="size-6" aria-hidden="true" />
            </div>
            <h3 className="mt-4 text-base font-semibold">No papers here yet</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Add papers from your library to make this collection useful.
            </p>
            <Button type="button" className="mt-4" onClick={onAddPaper}>
              <FilePlus2 className="size-4" aria-hidden="true" />
              Add Paper
            </Button>
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-auto">
          <div className="grid grid-cols-[minmax(360px,1fr)_126px_130px_96px_44px] items-center border-b border-border bg-muted/60 px-4 py-2.5 text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
            <span>Paper</span>
            <span>Category</span>
            <span>Updated</span>
            <span className="text-right">ID</span>
            <span className="sr-only">Actions</span>
          </div>
          <div className="divide-y divide-border">
            {papers.map((paper) => (
              <CollectionPaperRow
                key={paper.id}
                paper={paper}
                onRemove={onRemovePaper}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function CollectionPaperRow({
  onRemove,
  paper,
}: {
  onRemove: (paper: PaperListItem) => Promise<void>;
  paper: PaperListItem;
}) {
  const [isRemoving, setIsRemoving] = useState(false);
  const preview = paper.abstract?.trim() || "No abstract provided.";
  const updatedAt = paper.updated_at ?? paper.created_at;

  async function handleRemove() {
    setIsRemoving(true);

    try {
      await onRemove(paper);
    } catch (error) {
      toast.error("Could not remove paper", {
        description: getCollectionMutationError(error),
      });
    } finally {
      setIsRemoving(false);
    }
  }

  return (
    <div className="grid min-h-24 grid-cols-[minmax(360px,1fr)_126px_130px_96px_44px] items-center px-4 py-3 transition hover:bg-muted/35">
      <div className="min-w-0 pr-6">
        <div className="flex items-center gap-2">
          <FileText className="size-4 shrink-0 text-primary" aria-hidden="true" />
          <Link
            href={`/app/papers/${paper.id}`}
            className="min-w-0 rounded-sm focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/40"
          >
            <h3 className="truncate text-sm font-semibold hover:underline">
              {paper.title}
            </h3>
          </Link>
        </div>
        <p className="mt-2 line-clamp-2 text-sm leading-5 text-muted-foreground">
          {preview}
        </p>
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
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={`Remove ${paper.title}`}
        disabled={isRemoving}
        onClick={handleRemove}
      >
        {isRemoving ? (
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
        ) : (
          <X className="size-4" aria-hidden="true" />
        )}
      </Button>
    </div>
  );
}

function CollectionFormDialog({
  description,
  initialName = "",
  onOpenChange,
  onSaved,
  open,
  saveLabel,
  submitCollection,
  title,
}: {
  description: string;
  initialName?: string;
  onOpenChange: (open: boolean) => void;
  onSaved: (collection: Collection) => void;
  open: boolean;
  saveLabel: string;
  submitCollection: (payload: CollectionMutationPayload) => Promise<Collection>;
  title: string;
}) {
  const [name, setName] = useState(initialName);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const nameError = getCollectionNameError(name);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (nameError) {
      setError(nameError);
      return;
    }

    setError(null);
    setIsSaving(true);

    try {
      const collection = await submitCollection({ name: name.trim() });
      onSaved(collection);
    } catch (caughtError) {
      setError(getCollectionMutationError(caughtError));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!isSaving) {
          if (!nextOpen) {
            setName(initialName);
            setError(null);
          }
          onOpenChange(nextOpen);
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {error ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="collection-name">Name</Label>
            <Input
              id="collection-name"
              autoFocus
              disabled={isSaving}
              maxLength={COLLECTION_NAME_MAX_LENGTH}
              placeholder="My ML Papers"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={isSaving}
              onClick={() => {
                setName(initialName);
                setError(null);
                onOpenChange(false);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving || Boolean(nameError)}>
              {isSaving ? (
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Check className="size-4" aria-hidden="true" />
              )}
              {isSaving ? "Saving" : saveLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function DeleteCollectionDialog({
  collection,
  onDelete,
  onOpenChange,
  open,
}: {
  collection: Collection;
  onDelete: (collection: Collection) => Promise<void>;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleDelete() {
    setError(null);
    setIsDeleting(true);

    try {
      await onDelete(collection);
    } catch (caughtError) {
      setError(getCollectionMutationError(caughtError));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!isDeleting) {
          onOpenChange(nextOpen);
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mb-1 flex size-9 items-center justify-center rounded-md bg-destructive/10 text-destructive">
            <Trash2 className="size-4" aria-hidden="true" />
          </div>
          <DialogTitle>Delete collection?</DialogTitle>
          <DialogDescription>
            This will delete &quot;{collection.name}&quot;. Papers in your library
            will not be deleted.
          </DialogDescription>
        </DialogHeader>

        {error ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            disabled={isDeleting}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={isDeleting}
            onClick={handleDelete}
          >
            {isDeleting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="size-4" aria-hidden="true" />
            )}
            {isDeleting ? "Deleting" : "Delete collection"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddPaperDialog({
  collection,
  onCollectionUpdated,
  onOpenChange,
  open,
}: {
  collection: CollectionWithPapers;
  onCollectionUpdated: () => Promise<void>;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}) {
  const { apiRequest } = useAuth();
  const [papersState, setPapersState] = useState<PapersState>({
    status: "idle",
    data: null,
    error: null,
  });
  const [query, setQuery] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [addingPaperId, setAddingPaperId] = useState<number | null>(null);
  const collectionPaperIds = useMemo(
    () => new Set(collection.papers.map((paper) => paper.id)),
    [collection.papers],
  );

  useEffect(() => {
    if (!open) {
      return;
    }

    let isCurrent = true;

    async function loadPapers() {
      setPapersState({ status: "loading", data: null, error: null });

      try {
        const data = await apiRequest<PaginationResponse<PaperListItem>>(
          "/api/v1/papers",
          { query: { page: 1, limit: PAPER_PICKER_LIMIT } },
        );

        if (isCurrent) {
          setPapersState({ status: "success", data: data.items, error: null });
        }
      } catch (error) {
        if (isCurrent) {
          setPapersState({
            status: "error",
            data: null,
            error: getPaperPickerError(error),
          });
        }
      }
    }

    loadPapers();

    return () => {
      isCurrent = false;
    };
  }, [apiRequest, open, reloadKey]);

  const availablePapers =
    papersState.status === "success"
      ? papersState.data.filter((paper) => !collectionPaperIds.has(paper.id))
      : [];
  const filteredPapers = availablePapers.filter((paper) => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return true;
    }

    return (
      paper.title.toLowerCase().includes(normalizedQuery) ||
      (paper.abstract ?? "").toLowerCase().includes(normalizedQuery)
    );
  });

  async function handleAddPaper(paper: PaperListItem) {
    setAddingPaperId(paper.id);

    try {
      await apiRequest<{ message: string }>(
        `/api/v1/collections/${collection.id}/papers/${paper.id}`,
        { method: "POST" },
      );
      await onCollectionUpdated();
      toast.success("Paper added", {
        description: `${paper.title} was added to ${collection.name}.`,
      });
    } catch (error) {
      toast.error("Could not add paper", {
        description: getCollectionMutationError(error),
      });
    } finally {
      setAddingPaperId(null);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!addingPaperId) {
          onOpenChange(nextOpen);
        }
      }}
    >
      <DialogContent className="max-h-[calc(100vh-4rem)] overflow-hidden sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Add Paper</DialogTitle>
          <DialogDescription>
            Add a library paper through POST /api/v1/collections/{collection.id}
            /papers/{`{paper_id}`}.
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-2 rounded-md border border-input bg-background px-2.5">
          <Search className="size-4 text-muted-foreground" aria-hidden="true" />
          <Input
            className="border-0 px-0 shadow-none focus-visible:ring-0"
            placeholder="Search available papers"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>

        {papersState.status === "loading" ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-16 rounded-md" />
            ))}
          </div>
        ) : null}

        {papersState.status === "error" ? (
          <CollectionsError
            message={papersState.error}
            title="Could not load papers"
            onRetry={() => setReloadKey((value) => value + 1)}
          />
        ) : null}

        {papersState.status === "success" ? (
          <div className="max-h-[28rem] overflow-auto rounded-md border border-border">
            {filteredPapers.length === 0 ? (
              <div className="px-4 py-10 text-center">
                <p className="text-sm font-medium">No available papers</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  All matching papers are already in this collection.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {filteredPapers.map((paper) => (
                  <div
                    key={paper.id}
                    className="grid min-h-20 grid-cols-[1fr_96px] items-center px-4 py-3"
                  >
                    <div className="min-w-0 pr-5">
                      <h3 className="truncate text-sm font-medium">
                        {paper.title}
                      </h3>
                      <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">
                        {paper.abstract?.trim() || "No abstract provided."}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={Boolean(addingPaperId)}
                      onClick={() => handleAddPaper(paper)}
                    >
                      {addingPaperId === paper.id ? (
                        <Loader2
                          className="size-4 animate-spin"
                          aria-hidden="true"
                        />
                      ) : (
                        <Plus className="size-4" aria-hidden="true" />
                      )}
                      Add
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function CollectionsSkeleton() {
  return (
    <div className="grid min-h-[calc(100vh-13.5rem)] grid-cols-[360px_minmax(0,1fr)] overflow-hidden rounded-md border border-border bg-card">
      <div className="border-r border-border">
        <div className="flex h-12 items-center justify-between border-b border-border px-4">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="size-7" />
        </div>
        {Array.from({ length: 7 }).map((_, index) => (
          <div key={index} className="border-b border-border px-3 py-3">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="mt-2 h-3 w-32" />
          </div>
        ))}
      </div>
      <CollectionDetailSkeleton />
    </div>
  );
}

function CollectionDetailSkeleton() {
  return (
    <section className="p-5">
      <div className="border-b border-border pb-4">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="mt-3 h-8 w-96" />
        <div className="mt-3 flex gap-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-12" />
        </div>
      </div>
      <div className="mt-4 space-y-3">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-24 rounded-md" />
        ))}
      </div>
    </section>
  );
}

function CollectionsEmpty({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex min-h-80 items-center justify-center rounded-md border border-dashed border-border bg-card px-6 py-12 text-center">
      <div className="max-w-md">
        <div className="mx-auto flex size-12 items-center justify-center rounded-md bg-muted text-primary">
          <FolderKanban className="size-6" aria-hidden="true" />
        </div>
        <h2 className="mt-4 text-base font-semibold">No collections yet</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Create a collection, then add papers from your library.
        </p>
        <Button type="button" className="mt-4" onClick={onCreate}>
          <Plus className="size-4" aria-hidden="true" />
          New Collection
        </Button>
      </div>
    </div>
  );
}

function CollectionsError({
  message,
  onRetry,
  title,
}: {
  message: string;
  onRetry: () => void;
  title: string;
}) {
  return (
    <div className="rounded-md border border-destructive/30 bg-card px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex gap-3">
          <AlertCircle className="mt-0.5 size-5 shrink-0 text-destructive" />
          <div>
            <h2 className="text-sm font-semibold">{title}</h2>
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

function getCollectionNameError(name: string) {
  if (!name.trim()) {
    return "Collection name is required.";
  }

  if (name.length > COLLECTION_NAME_MAX_LENGTH) {
    return "Collection name must be 255 characters or fewer.";
  }

  return null;
}

function getCollectionLoadError(error: unknown) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again and reopen collections.";
    }

    if (error.status === 403) {
      return "You are not authorized to view these collections.";
    }

    if (error.status === 404) {
      return "The API could not find that collection.";
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while requesting collections.";
}

function getCollectionMutationError(error: unknown) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again and try once more.";
    }

    if (error.status === 403) {
      return "You are not authorized to change this collection.";
    }

    if (error.status === 404) {
      return "The API could not find that collection or paper.";
    }

    if (error.status === 422) {
      return error.message;
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while changing the collection.";
}

function getPaperPickerError(error: unknown) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again before loading papers.";
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while loading papers.";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}
