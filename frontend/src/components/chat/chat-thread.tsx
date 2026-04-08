"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
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
            {messages.map((m, idx) => (
              <div
                key={`${m.role}-${idx}-${m.content.slice(0, 24)}`}
                className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[min(100%,42rem)] rounded-2xl px-3.5 py-2.5 shadow-sm",
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
              </div>
            ))}
            {isSending ? (
              <div className="flex justify-start">
                <div className="max-w-[min(100%,42rem)] rounded-2xl border border-dashed border-border/50 bg-card/80 px-3.5 py-2.5 shadow-sm">
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
