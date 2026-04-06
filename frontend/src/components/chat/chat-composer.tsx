"use client";

import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { Loader2, SendHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const MIN_INPUT_PX = 48;
const MAX_INPUT_PX = 200;
/** Treat as multi-line once content needs more than one row (avoids jitter from subpixel). */
const MULTILINE_THRESHOLD_PX = MIN_INPUT_PX + 6;

export function ChatComposer({
  disabled,
  isSending,
  onSend,
}: {
  disabled: boolean;
  isSending: boolean;
  onSend: (text: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState("");
  const [multiline, setMultiline] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);

  const canSend = useMemo(() => draft.trim().length > 0 && !disabled && !isSending, [
    draft,
    disabled,
    isSending,
  ]);

  useLayoutEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    const sh = el.scrollHeight;
    const next = Math.min(Math.max(sh, MIN_INPUT_PX), MAX_INPUT_PX);
    el.style.height = `${next}px`;
    setMultiline(next >= MULTILINE_THRESHOLD_PX);
  }, [draft]);

  async function handleSend() {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    await onSend(text);
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        className={cn(
          "flex w-full min-w-0 gap-1.5 rounded-2xl border border-border/90 bg-card px-2 py-2 shadow-sm",
          multiline ? "items-end" : "items-center",
          "transition-[box-shadow,border-color] focus-within:border-ring/50 focus-within:ring-2 focus-within:ring-ring/25",
          disabled && "opacity-50",
        )}
      >
        <textarea
          ref={taRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Write a message…"
          disabled={disabled}
          rows={1}
          className={cn(
            "box-border min-h-[48px] w-full min-w-0 flex-1 resize-none",
            "border-0 bg-transparent px-2 py-3",
            "text-[0.9375rem] leading-6 text-foreground outline-none ring-0",
            "placeholder:text-muted-foreground/70",
            "focus-visible:ring-0",
            "disabled:cursor-not-allowed",
            "overflow-y-auto",
          )}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void handleSend();
          }}
        />
        <Button
          type="button"
          variant="default"
          size="sm"
          disabled={!canSend}
          className="shrink-0 gap-1.5 rounded-xl font-medium shadow-sm"
          onClick={() => void handleSend()}
        >
          {isSending ? (
            <Loader2 className="size-3.5 animate-spin" aria-hidden />
          ) : (
            <SendHorizontal className="size-3.5" strokeWidth={2.25} aria-hidden />
          )}
          {isSending ? "Sending…" : "Send"}
        </Button>
      </div>

      <p className="text-xs leading-relaxed text-muted-foreground">
        <kbd className="pointer-events-none rounded border border-border bg-muted/80 px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
          ⌘
        </kbd>
        <span className="mx-1">+</span>
        <kbd className="pointer-events-none rounded border border-border bg-muted/80 px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
          Enter
        </kbd>
        <span className="ml-2">to send</span>
      </p>

      {disabled ? (
        <p className="text-xs text-muted-foreground">Select a chat or wait until the API is ready.</p>
      ) : null}
    </div>
  );
}
