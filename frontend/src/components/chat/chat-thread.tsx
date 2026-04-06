"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/components/chat/types";

export function ChatThread({
  messages,
  isSending = false,
}: {
  messages: ChatMessage[];
  isSending?: boolean;
}) {
  return (
    <ScrollArea className="min-h-0 flex-1 rounded-2xl border border-border/70 bg-muted/25 shadow-inner">
      <div className="flex flex-col gap-4 p-4 md:p-5 md:pr-6">
        {messages.length === 0 ? (
          <div className="flex min-h-[180px] flex-col items-center justify-center px-4 py-12 text-center">
            <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
              No messages in this session yet. Say hello below to get started.
            </p>
          </div>
        ) : (
          <>
            {messages.map((m, idx) => (
              <div
                key={`${m.role}-${idx}-${m.content.slice(0, 24)}`}
                className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[min(100%,42rem)] rounded-2xl px-4 py-3 shadow-sm",
                    m.role === "user"
                      ? "bg-primary text-primary-foreground shadow-primary/20"
                      : "border border-border/80 bg-card text-card-foreground",
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
              </div>
            ))}
            {isSending ? (
              <div className="flex justify-start">
                <div className="max-w-[min(100%,42rem)] rounded-2xl border border-dashed border-border/80 bg-muted/40 px-4 py-3 shadow-sm">
                  <p className="text-[0.9375rem] leading-[1.65] text-muted-foreground">Thinking…</p>
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>
    </ScrollArea>
  );
}
