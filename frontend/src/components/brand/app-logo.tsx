"use client";

import Image from "next/image";

import { cn } from "@/lib/utils";

/** Intrinsic size of `/icon` (see `app/icon.tsx`); downscaled in layout for sharp nav. */
const ICON_SRC_SIZE = 256;

export function AppLogo({
  size = 36,
  className,
}: {
  /** Pixel width/height (square). */
  size?: number;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative shrink-0 overflow-hidden rounded-xl shadow-sm ring-1 ring-sidebar-border/45 dark:ring-white/10",
        className,
      )}
      style={{ width: size, height: size }}
    >
      <Image
        src="/icon"
        alt="AI Resume Agent"
        width={ICON_SRC_SIZE}
        height={ICON_SRC_SIZE}
        className="size-full object-cover"
        sizes={`${size}px`}
        quality={100}
        priority
        unoptimized
      />
    </div>
  );
}
