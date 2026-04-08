"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

const dialogContentClassName =
  "flex max-h-[90dvh] w-full max-w-4xl flex-col gap-4 overflow-hidden p-4 pt-6 sm:max-w-4xl";

const textareaClassName =
  "h-full min-h-[200px] resize-none overflow-y-auto [field-sizing:fixed]";

export type PasteJobDescriptionDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  value: string;
  onValueChange: (next: string) => void;
  placeholder?: string;
  error?: string | null;
  cancelLabel?: string;
  confirmLabel: string;
  confirmBusyLabel?: string;
  onConfirm: () => void | Promise<void>;
  isSubmitting?: boolean;
  /** When true, blocks submit even if the field has text (e.g. no session). */
  confirmDisabled?: boolean;
};

export function PasteJobDescriptionDialog({
  open,
  onOpenChange,
  title,
  description,
  value,
  onValueChange,
  placeholder = "Paste the full job description here…",
  error = null,
  cancelLabel = "Cancel",
  confirmLabel,
  confirmBusyLabel = "Saving…",
  onConfirm,
  isSubmitting = false,
  confirmDisabled = false,
}: PasteJobDescriptionDialogProps) {
  const busy = Boolean(isSubmitting);
  const canSubmit = value.trim().length > 0 && !confirmDisabled && !busy;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={dialogContentClassName}>
        <DialogHeader className="shrink-0 pr-8 text-left">
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
          <Textarea
            value={value}
            onChange={(e) => onValueChange(e.target.value)}
            placeholder={placeholder}
            disabled={busy}
            className={textareaClassName}
          />
          {error ? (
            <p className="shrink-0 text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}
        </div>
        <DialogFooter className="shrink-0 sm:mt-0">
          <Button type="button" variant="outline" disabled={busy} onClick={() => onOpenChange(false)}>
            {cancelLabel}
          </Button>
          <Button type="button" disabled={!canSubmit} onClick={() => void onConfirm()}>
            {busy ? confirmBusyLabel : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
