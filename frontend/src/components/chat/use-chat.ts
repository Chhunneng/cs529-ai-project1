"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { ChatMessage } from "@/components/chat/types";
import {
  apiChatRowToChatMessage,
  listSessionMessages,
  openAssistantReplyStream,
  postSessionMessage,
  type ApiChatRow,
  type SessionResponse,
} from "@/lib/api";

const WELCOME: ChatMessage = {
  role: "assistant",
  content:
    "Hi — link a resume template in Session tools, add a resume and optional job description, then ask for changes. Each reply can include a fresh PDF preview on the left once the worker finishes.",
};

export function useChat(
  sessionId: string | null,
  isOffline: boolean,
  sessionLinks: SessionResponse | null,
) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      setMessages([WELCOME]);
      return;
    }
    if (isOffline) return;

    let cancelled = false;
    listSessionMessages(sessionId)
      .then((rows) => {
        if (cancelled) return;
        setMessages(rows.length > 0 ? rows : [WELCOME]);
      })
      .catch(() => {
        if (cancelled) return;
        setMessages([WELCOME]);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, isOffline]);

  const canSend = useMemo(
    () => Boolean(sessionId) && !isOffline && !isSending,
    [sessionId, isOffline, isSending],
  );

  const latestPdfUrl = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant" && m.pdfDownloadUrl) return m.pdfDownloadUrl;
    }
    return null;
  }, [messages]);

  const sendMessage = useCallback(
    async (textRaw: string) => {
      const text = textRaw.trim();
      if (!text || !sessionId || isOffline || isSending) return;

      setIsSending(true);
      setMessages((prev) => [...prev, { role: "user", content: text }]);

      const streamRef: { current: EventSource | null } = { current: null };
      try {
        const userRow = await postSessionMessage({
          sessionId,
          content: text,
          resume_template_id: sessionLinks?.resume_template_id ?? undefined,
          resume_id: sessionLinks?.resume_id ?? undefined,
          job_description_id: sessionLinks?.job_description_id ?? undefined,
        });

        await new Promise<void>((resolve, reject) => {
          streamRef.current = openAssistantReplyStream(sessionId, userRow.id, {
            onEvent: (ev) => {
              if (ev.type === "assistant") {
                const row = ev.message as ApiChatRow;
                setMessages((prev) => [...prev, apiChatRowToChatMessage(row)]);
                resolve();
                return;
              }
              if (ev.type === "timeout") {
                setMessages((prev) => [
                  ...prev,
                  {
                    role: "assistant",
                    content:
                      ev.detail ??
                      "No assistant reply yet — check that the worker is running, Redis is up, and OPENAI_API_KEY is set on the worker.",
                  },
                ]);
                resolve();
                return;
              }
              setMessages((prev) => [
                ...prev,
                {
                  role: "assistant",
                  content:
                    ev.detail === "user_message_not_found"
                      ? "That message was not found for this session."
                      : "Could not load the assistant reply. Check the API and try again.",
                },
              ]);
              resolve();
            },
            onTransportError: () => {
              reject(new Error("assistant_stream_failed"));
            },
          });
        });
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              "Could not send your message or open the reply stream. Check the API URL, CORS, and backend logs.",
          },
        ]);
      } finally {
        streamRef.current?.close();
        streamRef.current = null;
        setIsSending(false);
      }
    },
    [isOffline, isSending, sessionId, sessionLinks],
  );

  return { messages, isSending, canSend, sendMessage, latestPdfUrl };
}
