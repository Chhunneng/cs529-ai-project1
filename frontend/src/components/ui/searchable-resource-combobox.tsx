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

const PANEL_MARGIN = 8;
const VIEWPORT_PAD = 8;
/** Search row: input + borders/padding (approximate, matches layout). */
const SEARCH_BLOCK_HEIGHT = 52;
/** Tailwind max-h-60 */
const LIST_MAX_CAP_PX = 240;
const PANEL_MAX_WIDTH_PX = 448;

function computePanelLayout(trigger: DOMRect): {
  top: number;
  left: number;
  width: number;
  listMaxHeight: number;
} {
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  const width = Math.min(trigger.width, vw - 2 * VIEWPORT_PAD, PANEL_MAX_WIDTH_PX);
  let left = trigger.left;
  left = Math.max(VIEWPORT_PAD, Math.min(left, vw - width - VIEWPORT_PAD));

  const spaceForListBelow = vh - trigger.bottom - PANEL_MARGIN - SEARCH_BLOCK_HEIGHT - VIEWPORT_PAD;
  const spaceForListAbove = trigger.top - PANEL_MARGIN - SEARCH_BLOCK_HEIGHT - VIEWPORT_PAD;

  const placeBelow = spaceForListBelow >= spaceForListAbove;
  let listMaxHeight = Math.min(
    LIST_MAX_CAP_PX,
    Math.max(48, placeBelow ? spaceForListBelow : spaceForListAbove),
  );

  let top: number;
  if (placeBelow) {
    top = trigger.bottom + PANEL_MARGIN;
  } else {
    top = trigger.top - PANEL_MARGIN - SEARCH_BLOCK_HEIGHT - listMaxHeight;
  }

  const panelBottom = () => top + SEARCH_BLOCK_HEIGHT + listMaxHeight;
  if (panelBottom() > vh - VIEWPORT_PAD) {
    listMaxHeight = Math.max(48, vh - VIEWPORT_PAD - top - SEARCH_BLOCK_HEIGHT);
  }
  if (top < VIEWPORT_PAD) {
    top = VIEWPORT_PAD;
    listMaxHeight = Math.min(
      listMaxHeight,
      Math.max(48, vh - VIEWPORT_PAD - top - SEARCH_BLOCK_HEIGHT),
    );
  }

  return { top, left, width, listMaxHeight };
}

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
  const onQueryChangeRef = useRef(onQueryChange);

  useLayoutEffect(() => {
    onQueryChangeRef.current = onQueryChange;
  }, [onQueryChange]);

  const [panelPos, setPanelPos] = useState({
    top: 0,
    left: 0,
    width: 0,
    listMaxHeight: LIST_MAX_CAP_PX,
  });

  const deferredOptions = useDeferredValue(options);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  useEffect(() => {
    if (!open) return;
    const fn = onQueryChangeRef.current;
    if (!fn) return;
    fn(deferredQuery);
  }, [open, deferredQuery]);

  const closeDropdown = useCallback(() => {
    setQuery("");
    setOpen(false);
  }, []);

  const updatePanelPosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setPanelPos(computePanelLayout(r));
  }, []);

  const refinePositionAfterPaint = useCallback(() => {
    const trigger = triggerRef.current;
    const panel = contentRef.current;
    if (!trigger || !panel) return;

    const r = trigger.getBoundingClientRect();
    const vh = window.innerHeight;
    const bottom = panel.getBoundingClientRect().bottom;
    if (bottom <= vh - VIEWPORT_PAD) return;

    const overflow = bottom - (vh - VIEWPORT_PAD);
    setPanelPos((prev) => {
      const nextList = Math.max(48, prev.listMaxHeight - overflow);
      if (nextList === prev.listMaxHeight) return prev;
      const placedBelow = prev.top >= r.bottom - 1;
      const nextTop = placedBelow
        ? prev.top
        : r.top - PANEL_MARGIN - SEARCH_BLOCK_HEIGHT - nextList;
      return { ...prev, listMaxHeight: nextList, top: nextTop };
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

  useLayoutEffect(() => {
    if (!open) return;
    const raf = requestAnimationFrame(() => refinePositionAfterPaint());
    return () => cancelAnimationFrame(raf);
  }, [open, filtered.length, noneValue, refinePositionAfterPaint]);

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
              <CommandList style={{ maxHeight: panelPos.listMaxHeight }} className="overflow-y-auto">
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
