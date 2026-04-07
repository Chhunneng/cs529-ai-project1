"use client";

import { ChatComposer } from "@/components/chat/chat-composer";
import { ContextPanel } from "@/components/chat/context-panel";
import { ChatThread } from "@/components/chat/chat-thread";
import { useChat } from "@/components/chat/use-chat";
import { useChatWorkspace } from "@/components/chat/use-chat-workspace";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";

export function ChatShell() {
  const { activeSessionId, retryConnection, isOffline, isReady } = useChatWorkspace();

  const { messages, isSending, canSend, sendMessage } = useChat(activeSessionId, isOffline);

  return (
    <main className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="flex flex-col gap-2 border-b border-border/80 bg-card/40 px-4 py-3 backdrop-blur-sm md:px-5">
          <div className="flex min-h-8 flex-col gap-0.5">
            <h1 className="text-base font-semibold tracking-tight text-foreground md:text-lg">
              Chat
            </h1>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Message the assistant and use the right panel to link resumes, jobs, and PDFs.
            </p>
          </div>
          {isOffline ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Can&apos;t reach the server</AlertTitle>
              <AlertDescription className="flex flex-col gap-2">
                <span>Check that the API is running and your app points to the correct URL.</span>
                <button
                  type="button"
                  className={buttonVariants({ variant: "outline", size: "sm", className: "w-fit" })}
                  onClick={() => retryConnection()}
                >
                  Retry
                </button>
              </AlertDescription>
            </Alert>
          ) : null}
        </header>

        <div className="flex min-h-0 flex-1 gap-4 p-3 md:gap-5 md:p-5">
          <Card className="flex min-w-0 flex-1 flex-col overflow-hidden border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
            <CardContent className="flex min-h-0 flex-1 flex-col gap-4 px-4 pt-4 pb-5 md:px-5">
              {!activeSessionId && !isOffline ? (
                <Empty className="min-h-[220px] border-none bg-muted/15 py-10">
                  <EmptyHeader>
                    <EmptyTitle className="font-semibold tracking-tight">Pick a conversation</EmptyTitle>
                    <EmptyDescription className="max-w-sm opacity-90">
                      Use <strong>New chat</strong> or choose a chat under Recent chats.
                    </EmptyDescription>
                  </EmptyHeader>
                </Empty>
              ) : activeSessionId ? (
                <ChatThread messages={messages} isSending={isSending} />
              ) : (
                <Empty className="min-h-[220px] border-none bg-muted/15 py-10">
                  <EmptyHeader>
                    <EmptyTitle className="font-semibold tracking-tight">You&apos;re offline</EmptyTitle>
                    <EmptyDescription>Connect to the server to send messages.</EmptyDescription>
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
  );
}
