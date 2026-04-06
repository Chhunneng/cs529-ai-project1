"use client";

import { useState } from "react";
import { MessageSquareText } from "lucide-react";

import { ChatComposer } from "@/components/chat/chat-composer";
import { ContextPanel } from "@/components/chat/context-panel";
import { ChatSidebar } from "@/components/chat/chat-sidebar";
import { ChatThread } from "@/components/chat/chat-thread";
import { useChat } from "@/components/chat/use-chat";
import { useChatWorkspace } from "@/components/chat/use-chat-workspace";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";

export function ChatShell() {
  const {
    sessions,
    activeSessionId,
    selectSession,
    createNewChat,
    removeSession,
    retryConnection,
    retryLoadSessions,
    sessionsLoading,
    sessionsError,
    isOffline,
    isChecking,
    isReady,
  } = useChatWorkspace();

  const { messages, isSending, canSend, sendMessage } = useChat(activeSessionId, isOffline);
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
        isChecking={isChecking}
        isReady={isReady}
        sessionsLoading={sessionsLoading}
        sessionsError={sessionsError}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-col gap-3 border-b border-border/80 bg-card/40 px-5 py-4 backdrop-blur-sm">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <MessageSquareText className="size-4" strokeWidth={2} />
            </div>
            <div className="min-w-0 flex-1 space-y-0.5">
              <h1 className="text-balance font-semibold text-lg tracking-tight text-foreground md:text-xl">
                Conversation
              </h1>
              <p className="text-pretty text-sm leading-relaxed text-muted-foreground">
                Ask for resume edits, tailoring, or PDF output — messages are saved with this session.
              </p>
            </div>
          </div>
          {newChatError ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>New chat failed</AlertTitle>
              <AlertDescription>{newChatError}</AlertDescription>
            </Alert>
          ) : null}
          {isOffline ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Backend unreachable</AlertTitle>
              <AlertDescription className="flex flex-col gap-2">
                <span>Check NEXT_PUBLIC_API_BASE_URL and that the API is running.</span>
                <Button className="w-fit" size="sm" variant="outline" onClick={() => retryConnection()}>
                  Retry
                </Button>
              </AlertDescription>
            </Alert>
          ) : null}
        </header>

        <div className="flex min-h-0 flex-1 gap-5 p-4 md:p-5">
          <Card className="flex min-w-0 flex-1 flex-col overflow-hidden border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
            <CardHeader className="space-y-1 border-b border-border/60 bg-muted/20 pb-4">
              <CardTitle className="text-base font-semibold tracking-tight">Thread</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                {activeSessionId
                  ? "Your messages and assistant replies for this session."
                  : "Choose a session from the sidebar or start a new chat."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex min-h-0 flex-1 flex-col gap-4 pt-5">
              {!activeSessionId && !isOffline ? (
                <Empty className="min-h-[220px] border-none bg-muted/15 py-10">
                  <EmptyHeader>
                    <EmptyTitle className="font-semibold tracking-tight">No chat selected</EmptyTitle>
                    <EmptyDescription className="max-w-sm opacity-90">
                      Use <strong>New chat</strong> in the sidebar or pick a session to continue.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : activeSessionId ? (
                <ChatThread messages={messages} isSending={isSending} />
              ) : (
                <Empty className="min-h-[220px] border-none bg-muted/15 py-10">
                  <EmptyHeader>
                    <EmptyTitle className="font-semibold tracking-tight">Offline</EmptyTitle>
                    <EmptyDescription>Connect to the API to use chat.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
              <ChatComposer
                disabled={!canSend}
                isSending={isSending}
                onSend={sendMessage}
              />
            </CardContent>
          </Card>

          <ContextPanel sessionId={activeSessionId} apiReady={isReady && !isOffline} />
        </div>
      </main>
    </div>
  );
}
