"use client";

import { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import { cn } from "@/lib/utils";

export function VirtualList<T>({
  items,
  estimateSize = 56,
  className,
  maxHeight = "min(60vh,480px)",
  children,
}: {
  items: readonly T[];
  estimateSize?: number;
  className?: string;
  maxHeight?: string;
  children: (item: T, index: number) => React.ReactNode;
}) {
  const parentRef = useRef<HTMLDivElement>(null);
  // TanStack Virtual returns non-memoizable helpers; safe here because we only pass measurements to DOM.
  // eslint-disable-next-line react-hooks/incompatible-library -- @tanstack/react-virtual useVirtualizer
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan: 8,
  });

  return (
    <div
      ref={parentRef}
      className={cn("overflow-auto", className)}
      style={{ maxHeight }}
    >
      <div
        className="relative w-full"
        style={{ height: virtualizer.getTotalSize() }}
      >
        {virtualizer.getVirtualItems().map((vi) => (
          <div
            key={vi.key}
            data-index={vi.index}
            ref={virtualizer.measureElement}
            className="absolute top-0 left-0 w-full"
            style={{ transform: `translateY(${vi.start}px)` }}
          >
            {children(items[vi.index], vi.index)}
          </div>
        ))}
      </div>
    </div>
  );
}
