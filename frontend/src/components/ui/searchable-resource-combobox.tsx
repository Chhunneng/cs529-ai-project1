"use client";

import {
  useCallback,
  useDeferredValue,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
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
  const triggerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [panelPos, setPanelPos] = useState({ top: 0, left: 0, width: 0 });
  const deferredOptions = useDeferredValue(options);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    if (!open || !onQueryChange) return;
    onQueryChange(deferredQuery);
  }, [open, deferredQuery, onQueryChange]);

  const closeDropdown = useCallback(() => {
    setQuery("");
    setOpen(false);
  }, []);

  const updatePanelPosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const margin = 4;
    setPanelPos({
      top: r.bottom + margin,
      left: r.left,
      width: r.width,
    });
  }, []);

  useLayoutEffect(() => {
    if (!open) return;
    updatePanelPosition();
    const el = triggerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => updatePanelPosition());
    ro.observe(el);
    window.addEventListener("scroll", updatePanelPosition, true);
    window.addEventListener("resize", updatePanelPosition);
    return () => {
      ro.disconnect();
      window.removeEventListener("scroll", updatePanelPosition, true);
      window.removeEventListener("resize", updatePanelPosition);
    };
  }, [open, updatePanelPosition]);

  const filtered = useMemo(() => {
    if (onQueryChange) return deferredOptions;
    const q = deferredQuery;
    if (!q) return deferredOptions;
    return deferredOptions.filter(
      (o) =>
        o.label.toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q) ||
        (o.description?.toLowerCase().includes(q) ?? false),
    );
  }, [deferredOptions, deferredQuery, onQueryChange]);

  const selectedLabel = useMemo(() => {
    if (noneValue != null && value === noneValue) return noneLabel;
    const hit = deferredOptions.find((o) => o.value === value);
    if (hit) return hit.label;
    if (fallbackLabel) return fallbackLabel;
    return placeholder;
  }, [deferredOptions, value, noneValue, noneLabel, fallbackLabel, placeholder]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t) || contentRef.current?.contains(t)) return;
      closeDropdown();
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open, closeDropdown]);

  const heightClass = size === "sm" ? "h-7 min-h-7" : "h-8 min-h-8";

  const dropdown =
    open && typeof document !== "undefined"
      ? createPortal(
          <div
            ref={contentRef}
            id={listboxId}
            role="listbox"
            className="fixed z-[200] overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-md"
            style={{
              top: panelPos.top,
              left: panelPos.left,
              width: panelPos.width,
              maxWidth: "min(100vw - 1rem, 28rem)",
            }}
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
              <CommandList className="max-h-60">
                <CommandEmpty>{emptyText}</CommandEmpty>
                <CommandGroup>
                  {noneValue != null ? (
                    <CommandItem
                      value={`${noneLabel}-${noneValue}`}
                      onSelect={() => {
                        onValueChange(noneValue);
                        closeDropdown();
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
                        closeDropdown();
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
          </div>,
          document.body,
        )
      : null;

  return (
    <div ref={triggerRef} className={cn("relative w-full", triggerClassName)}>
      <Button
        type="button"
        variant="outline"
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={open ? listboxId : undefined}
        id={`${listboxId}-trigger`}
        className={cn(
          "w-full justify-between gap-1.5 rounded-lg border-input bg-transparent px-2.5 font-normal shadow-none dark:bg-input/30 dark:hover:bg-input/50",
          heightClass,
          "text-sm",
          !selectedLabel || selectedLabel === placeholder ? "text-muted-foreground" : "text-foreground",
        )}
        onClick={() => {
          if (disabled) return;
          if (open) closeDropdown();
          else setOpen(true);
        }}
      >
        <span className="min-w-0 flex-1 truncate text-left">{selectedLabel}</span>
        <ChevronDownIcon className="size-4 shrink-0 opacity-60" aria-hidden />
      </Button>
      {totalHint ? (
        <p className="mt-1 text-[10px] leading-tight text-muted-foreground">{totalHint}</p>
      ) : null}
      {dropdown}
    </div>
  );
}
