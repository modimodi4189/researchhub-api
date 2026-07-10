"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Loader2, Lock, Save, Unlock, X } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { isApiError, type Paper } from "@/lib/api";
import type { PaperMutationPayload } from "@/lib/api/papers";
import { cn } from "@/lib/utils";

const PAPER_TITLE_MAX_LENGTH = 255;
const PAPER_ABSTRACT_MAX_LENGTH = 10_000;
const PAPER_CONTENT_MAX_LENGTH = 1_000_000;

const paperFormSchema = z.object({
  title: z
    .string()
    .min(1, "Title is required.")
    .max(PAPER_TITLE_MAX_LENGTH, "Title must be 255 characters or fewer.")
    .refine((value) => value.trim().length > 0, {
      message: "Title must not be blank.",
    }),
  abstract: z
    .string()
    .max(
      PAPER_ABSTRACT_MAX_LENGTH,
      "Abstract must be 10,000 characters or fewer.",
    )
    .optional(),
  content: z
    .string()
    .max(
      PAPER_CONTENT_MAX_LENGTH,
      "Content must be 1,000,000 characters or fewer.",
    )
    .optional(),
  is_public: z.boolean(),
  category_id: z
    .string()
    .refine(
      (value) => {
        const trimmed = value.trim();
        return trimmed === "" || /^[1-9]\d*$/.test(trimmed);
      },
      { message: "Category id must be a positive whole number." },
    ),
});

export type PaperFormValues = z.infer<typeof paperFormSchema>;

type PaperFormProps = {
  cancelLabel?: string;
  initialPaper?: Paper;
  onCancel: () => void;
  onSaved: (paper: Paper) => void;
  saveLabel?: string;
  submitPaper: (payload: PaperMutationPayload) => Promise<Paper>;
};

export function PaperForm({
  cancelLabel = "Cancel",
  initialPaper,
  onCancel,
  onSaved,
  saveLabel = "Save paper",
  submitPaper,
}: PaperFormProps) {
  const [apiError, setApiError] = useState<string | null>(null);
  const defaults = useMemo<PaperFormValues>(
    () => ({
      title: initialPaper?.title ?? "",
      abstract: initialPaper?.abstract ?? "",
      content: initialPaper?.content ?? "",
      is_public: initialPaper?.is_public ?? false,
      category_id: initialPaper?.category_id ? String(initialPaper.category_id) : "",
    }),
    [initialPaper],
  );
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
    setValue,
    control,
  } = useForm<PaperFormValues>({
    defaultValues: defaults,
    resolver: zodResolver(paperFormSchema),
  });
  const isPublic = useWatch({ control, name: "is_public" });

  async function onSubmit(values: PaperFormValues) {
    setApiError(null);

    try {
      const savedPaper = await submitPaper(toPaperPayload(values));
      reset(toPaperFormValues(savedPaper));
      onSaved(savedPaper);
    } catch (error) {
      setApiError(getPaperSaveError(error));
    }
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={handleSubmit(onSubmit)}>
      {apiError ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2.5">
          <div className="flex gap-2">
            <AlertCircle
              className="mt-0.5 size-4 shrink-0 text-destructive"
              aria-hidden="true"
            />
            <p className="text-sm leading-5 text-destructive">{apiError}</p>
          </div>
        </div>
      ) : null}

      <FieldGroup
        error={errors.title?.message}
        htmlFor="paper-title"
        label="Title"
      >
        <Input
          id="paper-title"
          aria-invalid={Boolean(errors.title)}
          disabled={isSubmitting}
          maxLength={PAPER_TITLE_MAX_LENGTH}
          placeholder="Machine Learning Introduction"
          {...register("title")}
        />
      </FieldGroup>

      <FieldGroup
        error={errors.abstract?.message}
        htmlFor="paper-abstract"
        label="Abstract"
      >
        <Textarea
          id="paper-abstract"
          aria-invalid={Boolean(errors.abstract)}
          className="min-h-28 resize-y"
          disabled={isSubmitting}
          placeholder="Short research abstract"
          {...register("abstract")}
        />
      </FieldGroup>

      <FieldGroup
        error={errors.content?.message}
        htmlFor="paper-content"
        label="Content"
      >
        <Textarea
          id="paper-content"
          aria-invalid={Boolean(errors.content)}
          className="min-h-56 resize-y"
          disabled={isSubmitting}
          placeholder="Full paper content"
          {...register("content")}
        />
      </FieldGroup>

      <div className="grid grid-cols-[minmax(0,1fr)_220px] gap-4">
        <FieldGroup
          error={errors.category_id?.message}
          htmlFor="paper-category-id"
          label="Category id"
        >
          <Input
            id="paper-category-id"
            aria-invalid={Boolean(errors.category_id)}
            disabled={isSubmitting}
            inputMode="numeric"
            placeholder="1"
            {...register("category_id")}
          />
        </FieldGroup>

        <div className="space-y-2">
          <Label>Visibility</Label>
          <button
            type="button"
            aria-pressed={isPublic}
            disabled={isSubmitting}
            className={cn(
              "flex h-8 w-full items-center justify-between rounded-lg border border-input px-2.5 text-sm transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50",
              isPublic
                ? "bg-primary-subtle text-accent-foreground"
                : "bg-background text-muted-foreground",
            )}
            onClick={() => setValue("is_public", !isPublic, { shouldDirty: true })}
          >
            <span className="flex items-center gap-2">
              {isPublic ? (
                <Unlock className="size-4" aria-hidden="true" />
              ) : (
                <Lock className="size-4" aria-hidden="true" />
              )}
              {isPublic ? "Public" : "Private"}
            </span>
            <span className="text-xs">{isPublic ? "On" : "Off"}</span>
          </button>
        </div>
      </div>

      <div className="flex justify-end gap-2 border-t border-border pt-4">
        <Button
          type="button"
          variant="outline"
          disabled={isSubmitting}
          onClick={onCancel}
        >
          <X className="size-4" aria-hidden="true" />
          {cancelLabel}
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Save className="size-4" aria-hidden="true" />
          )}
          {isSubmitting ? "Saving" : saveLabel}
        </Button>
      </div>
    </form>
  );
}

function FieldGroup({
  children,
  error,
  htmlFor,
  label,
}: {
  children: ReactNode;
  error?: string;
  htmlFor: string;
  label: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  );
}

function toPaperPayload(values: PaperFormValues): PaperMutationPayload {
  return {
    title: values.title,
    abstract: optionalText(values.abstract),
    content: optionalText(values.content),
    is_public: values.is_public,
    category_id: optionalPositiveInt(values.category_id),
  };
}

function toPaperFormValues(paper: Paper): PaperFormValues {
  return {
    title: paper.title,
    abstract: paper.abstract ?? "",
    content: paper.content ?? "",
    is_public: paper.is_public,
    category_id: paper.category_id ? String(paper.category_id) : "",
  };
}

function optionalText(value: string | undefined) {
  const trimmed = value?.trim();
  return trimmed ? value ?? null : null;
}

function optionalPositiveInt(value: string) {
  const trimmed = value.trim();
  return trimmed ? Number(trimmed) : null;
}

function getPaperSaveError(error: unknown) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Your session could not be verified. Log in again and try saving again.";
    }

    if (error.status === 403) {
      return "You are not authorized to edit this paper.";
    }

    if (error.status === 404) {
      return "The API could not find that paper or category.";
    }

    return `The API returned ${error.status}: ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unknown error occurred while saving the paper.";
}
