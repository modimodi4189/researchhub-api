"use client";

import { useState } from "react";
import { AlertTriangle, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type ConfirmDeleteDialogProps = {
  error?: string | null;
  isDeleting: boolean;
  onConfirm: () => Promise<void>;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  paperTitle: string;
};

export function ConfirmDeleteDialog({
  error,
  isDeleting,
  onConfirm,
  onOpenChange,
  open,
  paperTitle,
}: ConfirmDeleteDialogProps) {
  const [localError, setLocalError] = useState<string | null>(null);
  const shownError = error ?? localError;

  async function handleConfirm() {
    setLocalError(null);

    try {
      await onConfirm();
    } catch (caughtError) {
      setLocalError(getDialogError(caughtError));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!isDeleting) {
          onOpenChange(nextOpen);
          setLocalError(null);
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mb-1 flex size-9 items-center justify-center rounded-md bg-destructive/10 text-destructive">
            <AlertTriangle className="size-4" aria-hidden="true" />
          </div>
          <DialogTitle>Delete paper?</DialogTitle>
          <DialogDescription>
            This will permanently delete &quot;{paperTitle}&quot; from your library.
            This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        {shownError ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {shownError}
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
            onClick={handleConfirm}
          >
            {isDeleting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="size-4" aria-hidden="true" />
            )}
            {isDeleting ? "Deleting" : "Delete permanently"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function getDialogError(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return "The delete request failed. Try again.";
}
