"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { downloadFileFromUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/components/chat/types";

export function ChatThread({
  messages,
  isSending = false,
  hasOlderMessages = false,
  loadingOlder = false,
  onLoadOlder,
}: {
  messages: ChatMessage[];
  isSending?: boolean;
  hasOlderMessages?: boolean;
  loadingOlder?: boolean;
  onLoadOlder?: () => void | Promise<void>;
}) {
  const bottomAnchorRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (loadingOlder) return;
    bottomAnchorRef.current?.scrollIntoView({ block: "end", behavior: "auto" });
  }, [messages, isSending, loadingOlder]);

  return (
    <ScrollArea className="min-h-0 flex-1 bg-transparent">
      <div className="flex flex-col gap-3 pr-2 pl-0 py-1">
        {messages.length === 0 ? (
          <Empty className="min-h-[160px] border-none bg-transparent py-8">
            <EmptyHeader>
              <EmptyTitle className="text-base font-medium tracking-tight">No messages yet</EmptyTitle>
              <EmptyDescription className="max-w-sm opacity-90">
                Say hello below to get started with this session.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <>
            {hasOlderMessages && onLoadOlder ? (
              <div className="flex justify-center py-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 text-xs text-muted-foreground"
                  disabled={loadingOlder}
                  onClick={() => void onLoadOlder()}
                >
                  {loadingOlder ? "Loading…" : "Load older messages"}
                </Button>
              </div>
            ) : null}
            {messages.map((m, idx) => (
              <div
                key={m.id ?? `${m.role}-${idx}-${m.content.slice(0, 24)}`}
                className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "flex max-w-[min(100%,56rem)] flex-col gap-1.5",
                  )}
                >
                  <div
                    className={cn(
                      "rounded-2xl px-3.5 py-2.5 shadow-sm",
                      m.role === "user"
                        ? "bg-primary text-primary-foreground shadow-primary/25"
                        : "border border-border/50 bg-card text-card-foreground shadow-sm",
                    )}
                  >
                    <div
                      className={cn(
                        "whitespace-pre-wrap text-[0.9375rem] leading-[1.65]",
                        m.role === "user" ? "text-primary-foreground" : "text-foreground",
                      )}
                    >
                      {m.content}
                    </div>
                  </div>
                  {m.role === "assistant" && m.pdfDownloadUrl ? (
                    <ChatPdfAttachment downloadUrl={m.pdfDownloadUrl} />
                  ) : null}
                </div>
              </div>
            ))}
            {isSending ? (
              <div className="flex justify-start">
                <div className="max-w-[min(100%,56rem)] rounded-2xl border border-dashed border-border/50 bg-card/80 px-3.5 py-2.5 shadow-sm">
                  <p className="text-[0.9375rem] leading-[1.65] text-muted-foreground">Thinking…</p>
                </div>
              </div>
            ) : null}
          </>
        )}
        <div ref={bottomAnchorRef} aria-hidden className="h-0 w-full shrink-0" />
      </div>
    </ScrollArea>
  );
}

function ChatPdfAttachment({ downloadUrl }: { downloadUrl: string }) {
  const [busy, setBusy] = useState(false);

  const handleClick = async () => {
    setBusy(true);
    try {
      await downloadFileFromUrl(downloadUrl, "resume.pdf");
    } catch {
      window.open(downloadUrl, "_blank", "noopener,noreferrer");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      title="Download resume PDF"
      disabled={busy}
      onClick={() => void handleClick()}
      className={cn(
        "group inline-flex max-w-full min-w-0 items-center gap-2 self-start rounded-lg border border-border/80 bg-muted/40 px-2 py-1.5 text-left text-xs shadow-sm transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-60",
      )}
    >
      <FileText className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
      <span className="min-w-0 font-medium text-foreground">Resume PDF</span>
      {busy ? (
        <Loader2 className="size-3.5 shrink-0 animate-spin text-primary" aria-hidden />
      ) : (
        <Download className="size-3.5 shrink-0 text-primary" aria-hidden />
      )}
    </button>
  );
}
