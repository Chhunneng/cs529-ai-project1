"use client";

import Image from "next/image";

import { cn } from "@/lib/utils";

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
        src="/icon.png"
        alt="AI Resume Agent"
        width={size}
        height={size}
        className="size-full object-cover"
        priority
      />
    </div>
  );
}
