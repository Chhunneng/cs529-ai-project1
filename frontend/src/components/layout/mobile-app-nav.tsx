"use client";

import { useState } from "react";
import { Layers, Menu } from "lucide-react";

import type { SessionResponse } from "@/lib/api";
import { ChatSidebarPanel } from "@/components/layout/chat-sidebar-panel";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

export function MobileAppNav({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRetryLoadSessions,
  isChecking,
  isReady,
  sessionsLoading,
  sessionsError,
  newChatError = null,
  onDismissNewChatError,
  className,
}: {
  sessions: SessionResponse[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => Promise<void>;
  onDeleteSession: (id: string) => Promise<void>;
  onRetryLoadSessions: () => void;
  isChecking: boolean;
  isReady: boolean;
  sessionsLoading: boolean;
  sessionsError: string | null;
  newChatError?: string | null;
  onDismissNewChatError?: () => void;
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className={cn(
        "flex shrink-0 items-center gap-2 border-b border-border/80 bg-card/40 px-3 py-2.5 backdrop-blur-sm md:hidden",
        className,
      )}
    >
      <Sheet open={open} onOpenChange={setOpen}>
        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={() => setOpen(true)}
          aria-label="Open menu"
        >
          <Menu className="size-4" strokeWidth={2} />
        </Button>
        <SheetContent
          side="left"
          showCloseButton
          className="flex h-full w-[min(100%,20rem)] flex-col gap-0 overscroll-y-contain border-sidebar-border p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation and chats</SheetTitle>
          </SheetHeader>
          <ChatSidebarPanel
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={onSelectSession}
            onNewChat={onNewChat}
            onDeleteSession={onDeleteSession}
            onRetryLoadSessions={onRetryLoadSessions}
            isChecking={isChecking}
            isReady={isReady}
            sessionsLoading={sessionsLoading}
            sessionsError={sessionsError}
            newChatError={newChatError}
            onDismissNewChatError={onDismissNewChatError}
            onNavigate={() => setOpen(false)}
          />
        </SheetContent>
      </Sheet>
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-sm">
          <Layers className="size-4" strokeWidth={2.25} />
        </div>
        <div className="min-w-0">
          <div className="truncate font-semibold text-sm text-foreground">Resume Agent</div>
          <div className="truncate text-xs text-muted-foreground">Menu &amp; chats</div>
        </div>
      </div>
    </div>
  );
}
