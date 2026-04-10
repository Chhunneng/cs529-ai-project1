"use client";

import { useState } from "react";

import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { useChatWorkspace } from "@/components/chat/use-chat-workspace";
import { MobileAppNav } from "@/components/layout/mobile-app-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const {
    sessions,
    activeSessionId,
    selectSession,
    createNewChat,
    removeSession,
    retryLoadSessions,
    loadMoreSessions,
    sessionsTotal,
    sessionsLoadingMore,
    isChecking,
    isReady,
    sessionsLoading,
    sessionsError,
  } = useChatWorkspace();

  const [newChatError, setNewChatError] = useState<string | null>(null);

  async function handleNewChat() {
    setNewChatError(null);
    try {
      await createNewChat();
    } catch {
      setNewChatError("Could not create session. Check the API and try again.");
    }
  }

  return (
    <div className="flex h-dvh w-full bg-background bg-[radial-gradient(ellipse_120%_80%_at_50%_-20%,oklch(0.42_0.17_265/0.08),transparent)]">
      <ChatSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={(id) => removeSession(id)}
        onRetryLoadSessions={() => retryLoadSessions()}
        onLoadMoreSessions={() => void loadMoreSessions()}
        sessionsTotal={sessionsTotal}
        sessionsLoadingMore={sessionsLoadingMore}
        isChecking={isChecking}
        isReady={isReady}
        sessionsLoading={sessionsLoading}
        sessionsError={sessionsError}
        newChatError={newChatError}
        onDismissNewChatError={() => setNewChatError(null)}
      />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <MobileAppNav
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={selectSession}
          onNewChat={handleNewChat}
          onDeleteSession={(id) => removeSession(id)}
          onRetryLoadSessions={() => retryLoadSessions()}
          onLoadMoreSessions={() => void loadMoreSessions()}
          sessionsTotal={sessionsTotal}
          sessionsLoadingMore={sessionsLoadingMore}
          isChecking={isChecking}
          isReady={isReady}
          sessionsLoading={sessionsLoading}
          sessionsError={sessionsError}
          newChatError={newChatError}
          onDismissNewChatError={() => setNewChatError(null)}
        />
        {children}
      </div>
    </div>
  );
}
