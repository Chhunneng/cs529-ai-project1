"use client";

import { useMemo, useState } from "react";

import { ChatComposer } from "@/components/chat/chat-composer";
import { ContextPanel } from "@/components/chat/context-panel";
import { ChatThread } from "@/components/chat/chat-thread";
import { ResumePdfPreview } from "@/components/chat/resume-pdf-preview";
import { useChat } from "@/components/chat/use-chat";
import { useChatWorkspace } from "@/components/chat/use-chat-workspace";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { useMediaQuery } from "@/hooks/use-media-query";
import type { ChatMessage } from "@/components/chat/types";

export function ChatShell() {
  const { activeSessionId, sessions, retryConnection, isOffline, isReady } = useChatWorkspace();
  const showInlineContext = useMediaQuery("(min-width: 1024px)");
  const [sessionSheetOpen, setSessionSheetOpen] = useState(false);

  const sessionRow = useMemo(
    () => sessions.find((s) => String(s.id) === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

  const { messages, isSending, canSend, sendMessage, latestPdfUrl } = useChat(
    activeSessionId,
    isOffline,
    sessionRow,
  );

  const apiOk = isReady && !isOffline;

  return (
    <main className="flex min-h-0 min-w-0 flex-1 flex-col">
      <header className="flex flex-col gap-2 border-b border-border/80 bg-card/40 px-4 py-3 backdrop-blur-sm md:px-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div className="flex min-h-8 min-w-0 flex-1 flex-col gap-0.5">
            <h1 className="text-base font-semibold tracking-tight text-foreground md:text-lg">Chat</h1>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {showInlineContext
                ? "PDF preview on the left; chat on the right. Use Session tools to link resume, job, and template."
                : "PDF preview stacks above chat on small screens. Use Session tools to link resume, job, and template."}
            </p>
          </div>
          {!showInlineContext ? (
            <Sheet open={sessionSheetOpen} onOpenChange={setSessionSheetOpen}>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="shrink-0 self-start sm:self-center"
                onClick={() => setSessionSheetOpen(true)}
              >
                Session tools
              </Button>
              <SheetContent
                side="right"
                showCloseButton
                className="flex w-full flex-col gap-0 overflow-hidden overscroll-y-contain p-0 sm:max-w-lg"
              >
                <SheetHeader className="shrink-0 border-b border-border/80 px-4 py-4 text-left">
                  <SheetTitle>Session workspace</SheetTitle>
                  <SheetDescription>
                    Link resumes, job descriptions, and templates for this chat, then generate a PDF.
                  </SheetDescription>
                </SheetHeader>
                <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
                  <ContextPanel
                    sessionId={activeSessionId}
                    apiReady={apiOk}
                    variant="embedded"
                  />
                </div>
              </SheetContent>
            </Sheet>
          ) : null}
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

      <div className="flex min-h-0 flex-1 flex-col gap-2 p-2 md:flex-row md:gap-0 md:p-2">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col md:hidden">
          <ResumePdfPreview pdfUrl={latestPdfUrl} />
          <div className="mt-2 flex min-h-0 min-w-0 flex-1 flex-col">
            <ChatColumn
              activeSessionId={activeSessionId}
              isOffline={isOffline}
              messages={messages}
              isSending={isSending}
              canSend={canSend}
              sendMessage={sendMessage}
            />
          </div>
        </div>

        <div className="hidden min-h-0 min-w-0 flex-1 md:flex">
          {/* Flex split (no extra deps) — avoids stale Docker named volumes missing react-resizable-panels */}
          <div className="flex min-h-[420px] min-w-0 flex-1 rounded-lg border border-border/50">
            <div className="flex min-h-0 min-w-0 flex-[11] flex-col p-2">
              <ResumePdfPreview pdfUrl={latestPdfUrl} />
            </div>
            <div className="w-px shrink-0 bg-border/80" aria-hidden />
            <div className="flex min-h-0 min-w-0 flex-[14] flex-col p-2">
              <ChatColumn
                activeSessionId={activeSessionId}
                isOffline={isOffline}
                messages={messages}
                isSending={isSending}
                canSend={canSend}
                sendMessage={sendMessage}
              />
            </div>
          </div>
        </div>

        {showInlineContext ? (
          <ContextPanel sessionId={activeSessionId} apiReady={apiOk} variant="sidebar" />
        ) : null}
      </div>
    </main>
  );
}

function ChatColumn({
  activeSessionId,
  isOffline,
  messages,
  isSending,
  canSend,
  sendMessage,
}: {
  activeSessionId: string | null;
  isOffline: boolean;
  messages: ChatMessage[];
  isSending: boolean;
  canSend: boolean;
  sendMessage: (t: string) => Promise<void>;
}) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex min-h-0 min-w-0 w-full max-w-3xl flex-1 flex-col gap-2">
        {!activeSessionId && !isOffline ? (
          <Empty className="min-h-[200px] border-none bg-transparent py-8">
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
          <Empty className="min-h-[200px] border-none bg-transparent py-8">
            <EmptyHeader>
              <EmptyTitle className="font-semibold tracking-tight">You&apos;re offline</EmptyTitle>
              <EmptyDescription>Connect to the server to send messages.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
        <Separator className="bg-border/50" />
        <ChatComposer disabled={!canSend} isSending={isSending} onSend={sendMessage} />
      </div>
    </div>
  );
}
