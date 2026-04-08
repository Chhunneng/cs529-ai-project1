"use client";

import { Menu } from "@base-ui/react/menu";
import Link from "next/link";
import { ChevronDown } from "lucide-react";

import { SIDEBAR_NAV, navActive } from "@/components/layout/app-nav";
import { cn } from "@/lib/utils";

export function SidebarNavMenu({
  pathname,
  onNavigate,
  onDismissNewChatError,
}: {
  pathname: string;
  onNavigate?: () => void;
  onDismissNewChatError?: () => void;
}) {
  const active = SIDEBAR_NAV.find((item) => navActive(pathname, item.href)) ?? SIDEBAR_NAV[0];
  const ActiveIcon = active.icon;

  return (
    <Menu.Root modal={false}>
      <Menu.Trigger
        className={cn(
          "group flex w-full flex-row items-center justify-between gap-2 rounded-lg border border-sidebar-border/70 bg-muted/15 px-2.5 py-2 text-left text-sm transition-colors outline-none select-none",
          "focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar",
          "text-sidebar-foreground hover:bg-sidebar-accent data-popup-open:bg-sidebar-accent",
        )}
      >
        <span className="flex min-w-0 flex-1 items-center gap-3">
          <span
            className="flex size-8 shrink-0 items-center justify-center rounded-md border border-sidebar-border/80 bg-sidebar-primary/15 text-sidebar-primary"
            aria-hidden
          >
            <ActiveIcon className="size-4" strokeWidth={2} />
          </span>
          <span className="min-w-0 truncate font-medium leading-snug">{active.label}</span>
        </span>
        <ChevronDown
          className="size-4 shrink-0 text-muted-foreground opacity-80 transition-transform duration-200 group-data-popup-open:rotate-180"
          strokeWidth={2}
          aria-hidden
        />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner side="bottom" align="start" sideOffset={4} className="isolate z-50 outline-none">
          <Menu.Popup
            className={cn(
              "min-w-(--anchor-width) max-w-[min(100vw-1.5rem,16rem)] origin-(--transform-origin) rounded-lg border border-sidebar-border/80 bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10",
              "data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
            )}
          >
            {SIDEBAR_NAV.map((item) => {
              const isActive = navActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <Menu.LinkItem
                  key={item.href}
                  label={item.label}
                  render={
                    <Link
                      href={item.href}
                      onClick={() => {
                        onDismissNewChatError?.();
                        onNavigate?.();
                      }}
                    />
                  }
                  closeOnClick
                  className={cn(
                    "flex w-full cursor-default flex-row items-center gap-2 rounded-md px-2 py-2 text-sm outline-none select-none",
                    "data-highlighted:bg-sidebar-accent data-highlighted:text-sidebar-accent-foreground",
                    isActive && "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
                  )}
                >
                  <span
                    className={cn(
                      "flex size-7 shrink-0 items-center justify-center rounded-md border border-transparent text-muted-foreground",
                      isActive && "border-sidebar-border/80 bg-sidebar-primary/15 text-sidebar-primary",
                    )}
                    aria-hidden
                  >
                    <Icon className="size-3.5" strokeWidth={2} />
                  </span>
                  <span className="min-w-0 leading-snug">{item.label}</span>
                </Menu.LinkItem>
              );
            })}
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}
