import { cn } from "@/lib/utils";

/** Shared list row chrome for pickers (resume recent, template library, etc.). */
export const listRowBase =
  "rounded-lg border border-border/70 bg-muted/10 transition-colors hover:bg-muted/20";

/** Applied when the row is the current selection. */
export const listRowSelected = "border-primary/45 bg-muted/30 ring-1 ring-ring/35";

export function listRowClasses(selected: boolean) {
  return cn(listRowBase, selected && listRowSelected);
}
