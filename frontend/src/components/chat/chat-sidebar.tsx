"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Briefcase,
  FileDown,
  FileText,
  Layers,
  LayoutTemplate,
  MessageCirclePlus,
  MessageSquare,
  Trash2,
} from "lucide-react";

import type { SessionResponse } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const SIDEBAR_NAV = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/resumes", label: "Resumes", icon: FileText },
  { href: "/job-descriptions", label: "Jobs", icon: Briefcase },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/outputs", label: "PDF exports", icon: FileDown },
] as const;

function navActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function formatUpdatedAt(iso: string) {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export function ChatSidebar({
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
}) {
  const pathname = usePathname();
  const [isCreating, setIsCreating] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleNewChat() {
    if (!isReady || isCreating) return;
    setIsCreating(true);
    try {
      await onNewChat();
    } finally {
      setIsCreating(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDeleteId) return;
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await onDeleteSession(pendingDeleteId);
      setPendingDeleteId(null);
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : "Could not delete session.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <aside className="hidden h-dvh w-[300px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex lg:w-80">
      <div className="flex flex-col gap-3 p-5 pb-2">
        <div className="flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-xl bg-sidebar-primary text-sidebar-primary-foreground shadow-sm">
            <Layers className="size-4" strokeWidth={2.25} />
          </div>
          <div className="min-w-0">
            <div className="truncate font-semibold text-base text-sidebar-foreground tracking-tight">
              Resume Agent
            </div>
            <div className="truncate text-xs leading-snug text-muted-foreground">
              Your conversations
            </div>
          </div>
        </div>
      </div>

      <nav className="flex flex-col gap-2 px-3 pb-3" aria-label="Main">
        <div className="px-1">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Navigation
          </div>
        </div>
        <div className="flex flex-col gap-0.5 rounded-xl border border-sidebar-border/70 bg-muted/15 p-1.5 shadow-sm backdrop-blur-sm">
          {SIDEBAR_NAV.map((item) => {
            const active = navActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                onClick={() => onDismissNewChatError?.()}
                className={cn(
                  "flex flex-row items-center gap-3 rounded-lg px-2 py-2 text-sm transition-colors outline-none",
                  "focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar",
                  active
                    ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground shadow-sm"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/70",
                )}
              >
                <span
                  className={cn(
                    "flex size-8 shrink-0 items-center justify-center rounded-md border border-transparent",
                    active
                      ? "border-sidebar-border/80 bg-sidebar-primary/15 text-sidebar-primary"
                      : "bg-background/60 text-muted-foreground",
                  )}
                  aria-hidden
                >
                  <Icon className="size-4" strokeWidth={2} />
                </span>
                <span className="min-w-0 leading-snug">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      <Separator className="bg-sidebar-border" />

      {newChatError ? (
        <div className="px-5 pt-2">
          <Alert variant="destructive" className="border-destructive/40 py-2">
            <AlertTitle className="text-xs">New chat failed</AlertTitle>
            <AlertDescription className="text-xs">{newChatError}</AlertDescription>
            {onDismissNewChatError ? (
              <button
                type="button"
                className="mt-2 text-xs font-medium underline underline-offset-4"
                onClick={() => onDismissNewChatError()}
              >
                Dismiss
              </button>
            ) : null}
          </Alert>
        </div>
      ) : null}

      <div className="px-5 pb-4 pt-2">
        <Button
          className="w-full gap-2 font-medium shadow-sm"
          size="default"
          disabled={!isReady || isCreating || isChecking || sessionsLoading}
          onClick={() => void handleNewChat()}
        >
          <MessageCirclePlus className="size-4" strokeWidth={2} />
          New chat
        </Button>
      </div>
      <Separator className="bg-sidebar-border" />
      <div className="px-5 pb-2 pt-4">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Recent chats
        </div>
      </div>
      <ScrollArea className="min-h-0 flex-1 px-3 pb-5">
        <div className="flex flex-col gap-1.5 pr-1">
          {sessionsError ? (
            <div className="flex flex-col gap-2 rounded-xl border border-destructive/25 bg-destructive/5 px-3 py-3">
              <div className="text-xs leading-relaxed text-destructive">{sessionsError}</div>
              <Button variant="outline" size="sm" className="w-full" onClick={onRetryLoadSessions}>
                Retry
              </Button>
            </div>
          ) : isChecking || (isReady && sessionsLoading) ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="min-h-[4.25rem] w-full rounded-xl" />
              <Skeleton className="min-h-[4.25rem] w-full rounded-xl" />
              <Skeleton className="min-h-[4.25rem] w-full rounded-xl" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-sidebar-border bg-muted/20 px-3 py-8 text-center text-xs leading-relaxed text-muted-foreground">
              No chats yet. Start with <strong>New chat</strong>.
            </div>
          ) : (
            sessions.map((row) => {
              const id = String(row.id);
              return (
                <div
                  key={id}
                  className={cn(
                    "group relative flex items-start gap-0.5 rounded-xl border border-transparent transition-colors",
                    "hover:bg-sidebar-accent/80",
                    id === activeSessionId &&
                      "border-sidebar-border bg-sidebar-accent text-sidebar-accent-foreground shadow-sm",
                    id !== activeSessionId && "text-sidebar-foreground",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => onSelectSession(id)}
                    className={cn(
                      "min-w-0 flex-1 rounded-l-xl px-3 py-2.5 text-left transition-colors",
                      "hover:bg-transparent",
                      id === activeSessionId ? "text-sidebar-accent-foreground" : "",
                    )}
                  >
                    <span
                      className="block break-all font-mono text-[11px] font-medium leading-snug tracking-tight"
                      title={id}
                    >
                      {id}
                    </span>
                    <span
                      className={cn(
                        "mt-1 block text-[10px] leading-tight tabular-nums",
                        id === activeSessionId
                          ? "text-sidebar-accent-foreground/75"
                          : "text-muted-foreground",
                      )}
                    >
                      Updated {formatUpdatedAt(row.updated_at)}
                    </span>
                  </button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    disabled={!isReady || isDeleting}
                    className={cn(
                      "mt-1.5 mr-1 shrink-0 rounded-lg text-muted-foreground hover:text-destructive",
                      "opacity-70 group-hover:opacity-100",
                    )}
                    aria-label={`Delete session ${id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setDeleteError(null);
                      setPendingDeleteId(id);
                    }}
                  >
                    <Trash2 className="size-3.5" strokeWidth={2} />
                  </Button>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>

      <Dialog
        open={pendingDeleteId != null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDeleteId(null);
            setDeleteError(null);
          }
        }}
      >
        <DialogContent showCloseButton className="gap-0 sm:max-w-md">
          <DialogHeader className="space-y-2 pr-8 text-left">
            <DialogTitle className="leading-snug">Delete this session?</DialogTitle>
            <DialogDescription>
              This removes the session and all related data: chat messages, agent runs, job
              descriptions for this session, resume outputs, and generated PDF/TeX files when they
              live under the server artifacts folder. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteError ? (
            <p className="mt-3 text-sm leading-relaxed text-destructive">{deleteError}</p>
          ) : null}
          <div className="mt-4 flex flex-col-reverse gap-2 border-t border-border/70 pt-3 sm:flex-row sm:justify-end sm:gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={isDeleting}
              className="w-full sm:w-auto"
              onClick={() => {
                setPendingDeleteId(null);
                setDeleteError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={isDeleting}
              className="w-full font-medium sm:w-auto"
              onClick={() => void confirmDelete()}
            >
              {isDeleting ? "Deleting…" : "Delete session"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </aside>
  );
}
