"use client";

import {
  useCallback,
  useDeferredValue,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { Popover } from "@base-ui/react/popover";
import { ChevronDownIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandItem, CommandList } from "@/components/ui/command";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export type ResourceOption = {
  value: string;
  label: string;
  description?: string;
};

export function SearchableResourceCombobox({
  value,
  onValueChange,
  options,
  placeholder = "Choose…",
  searchPlaceholder = "Search…",
  emptyText = "No matches.",
  disabled,
  triggerClassName,
  size = "sm",
  noneValue,
  noneLabel = "None",
  fallbackLabel,
  totalHint,
  id,
  /** When set, called with debounced search text so the parent can refetch options (server-side filter). */
  onQueryChange,
}: {
  value: string;
  onValueChange: (v: string) => void;
  options: ResourceOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  triggerClassName?: string;
  size?: "sm" | "default";
  noneValue?: string;
  noneLabel?: string;
  fallbackLabel?: string | null;
  totalHint?: string | null;
  id?: string;
  onQueryChange?: (q: string) => void;
}) {
  const autoId = useId();
  const listboxId = id ?? `resource-combobox-${autoId}`;
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const onQueryChangeRef = useRef(onQueryChange);

  useEffect(() => {
    onQueryChangeRef.current = onQueryChange;
  }, [onQueryChange]);

  const deferredOptions = useDeferredValue(options);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    if (!open) return;
    const fn = onQueryChangeRef.current;
    if (!fn) return;
    fn(deferredQuery);
  }, [open, deferredQuery]);

  const handleOpenChange = useCallback((next: boolean) => {
    setOpen(next);
    if (!next) setQuery("");
  }, []);

  const serverSideFilter = onQueryChange != null;

  const filtered = useMemo(() => {
    if (serverSideFilter) return deferredOptions;
    const q = deferredQuery;
    if (!q) return deferredOptions;
    return deferredOptions.filter(
      (o) =>
        o.label.toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q) ||
        (o.description?.toLowerCase().includes(q) ?? false),
    );
  }, [deferredOptions, deferredQuery, serverSideFilter]);

  const selectedLabel = useMemo(() => {
    if (noneValue != null && value === noneValue) return noneLabel;
    const hit = deferredOptions.find((o) => o.value === value);
    if (hit) return hit.label;
    if (fallbackLabel) return fallbackLabel;
    return placeholder;
  }, [deferredOptions, value, noneValue, noneLabel, fallbackLabel, placeholder]);

  const heightClass = size === "sm" ? "h-7 min-h-7" : "h-8 min-h-8";

  return (
    <div className={cn("relative w-full", triggerClassName)}>
      <Popover.Root open={open} onOpenChange={handleOpenChange} modal={false}>
        <Popover.Trigger
          disabled={disabled}
          id={`${listboxId}-trigger`}
          nativeButton
          render={
            <Button
              type="button"
              variant="outline"
              disabled={disabled}
              aria-expanded={open}
              aria-haspopup="listbox"
              aria-controls={open ? listboxId : undefined}
              className={cn(
                "w-full justify-between gap-1.5 rounded-lg border-input bg-transparent px-2.5 font-normal shadow-none dark:bg-input/30 dark:hover:bg-input/50",
                heightClass,
                "text-sm",
                !selectedLabel || selectedLabel === placeholder ? "text-muted-foreground" : "text-foreground",
              )}
            />
          }
        >
          <span className="min-w-0 flex-1 truncate text-left">{selectedLabel}</span>
          <ChevronDownIcon className="size-4 shrink-0 opacity-60" aria-hidden />
        </Popover.Trigger>

        <Popover.Portal>
          <Popover.Positioner
            side="bottom"
            align="start"
            sideOffset={8}
            collisionPadding={8}
            className="isolate z-[200] w-(--anchor-width) min-w-(--anchor-width) max-w-[min(100vw-1rem,28rem)]"
          >
            <Popover.Popup
              id={listboxId}
              role="listbox"
              initialFocus
              className="max-h-[min(var(--available-height,70vh),20rem)] w-full overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-md outline-none"
            >
              <Command shouldFilter={false}>
                <div className="border-b border-border/60 p-1.5">
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={searchPlaceholder}
                    className={cn("h-8", size === "sm" && "text-sm")}
                    aria-label={searchPlaceholder}
                  />
                </div>
                <CommandList className="max-h-60 overflow-y-auto">
                  <CommandEmpty>{emptyText}</CommandEmpty>
                  <CommandGroup>
                    {noneValue != null ? (
                      <CommandItem
                        value={`${noneLabel}-${noneValue}`}
                        onSelect={() => {
                          onValueChange(noneValue);
                          handleOpenChange(false);
                        }}
                      >
                        {noneLabel}
                      </CommandItem>
                    ) : null}
                    {filtered.map((opt) => (
                      <CommandItem
                        key={opt.value}
                        value={opt.value}
                        onSelect={() => {
                          onValueChange(opt.value);
                          handleOpenChange(false);
                        }}
                      >
                        <div className="flex min-w-0 flex-1 flex-col gap-0.5 text-left">
                          <span className="truncate">{opt.label}</span>
                          {opt.description ? (
                            <span className="truncate text-xs text-muted-foreground">{opt.description}</span>
                          ) : null}
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </Popover.Popup>
          </Popover.Positioner>
        </Popover.Portal>
      </Popover.Root>
      {totalHint ? (
        <p className="mt-1 text-[10px] leading-tight text-muted-foreground">{totalHint}</p>
      ) : null}
    </div>
  );
}
