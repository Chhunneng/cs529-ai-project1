"use client";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TemplatesManageCore } from "@/components/templates/templates-manage-core";

export function TemplateManagerSheet({
  open,
  onOpenChange,
  onTemplatesChanged,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTemplatesChanged?: () => void;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        showCloseButton
        side="right"
        className="flex h-full w-[min(95vw,56rem)] max-w-none flex-col gap-0 overflow-hidden p-0 sm:max-w-none"
      >
        <SheetHeader className="shrink-0 gap-1 border-b border-border px-4 py-4">
          <SheetTitle>Manage templates</SheetTitle>
          <SheetDescription>
            Create and edit LaTeX templates used for resume PDF rendering.
          </SheetDescription>
        </SheetHeader>

        <TemplatesManageCore
          active={open}
          onTemplatesChanged={onTemplatesChanged}
          scrollAreaClassName="min-h-0 w-full flex-1"
        />
      </SheetContent>
    </Sheet>
  );
}
