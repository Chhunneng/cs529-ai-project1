"use client";

import type { SessionResponse } from "@/lib/api";
import { ChatSidebarPanel } from "@/components/layout/chat-sidebar-panel";

export function ChatSidebar({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRetryLoadSessions,
  onLoadMoreSessions,
  sessionsTotal,
  sessionsLoadingMore,
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
  onLoadMoreSessions?: () => void | Promise<void>;
  sessionsTotal?: number;
  sessionsLoadingMore?: boolean;
  isChecking: boolean;
  isReady: boolean;
  sessionsLoading: boolean;
  sessionsError: string | null;
  newChatError?: string | null;
  onDismissNewChatError?: () => void;
}) {
  return (
    <aside className="hidden h-dvh w-[260px] shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex lg:w-72 xl:w-80">
      <ChatSidebarPanel
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={onSelectSession}
        onNewChat={onNewChat}
        onDeleteSession={onDeleteSession}
        onRetryLoadSessions={onRetryLoadSessions}
        onLoadMoreSessions={onLoadMoreSessions}
        sessionsTotal={sessionsTotal}
        sessionsLoadingMore={sessionsLoadingMore}
        isChecking={isChecking}
        isReady={isReady}
        sessionsLoading={sessionsLoading}
        sessionsError={sessionsError}
        newChatError={newChatError}
        onDismissNewChatError={onDismissNewChatError}
      />
    </aside>
  );
}
