"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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
    "Hi — link a resume template in Session tools, add a resume, and add a job description, then ask for changes. When you want a PDF, use Generate PDF in Session tools.",
};

const SESSION_LINKS_HINT =
  "Choose a resume, template, and job description in Session tools before you send a message.";

const MESSAGE_WINDOW = 120;

function requiredLinkIds(
  s: SessionResponse | null | undefined,
): { resume_template_id: string; resume_id: string; job_description_id: string } | null {
  const r = s?.resume_id;
  const t = s?.resume_template_id;
  const j = s?.job_description_id;
  if (!r || !t || !j) return null;
  return { resume_id: r, resume_template_id: t, job_description_id: j };
}

export function useChat(
  sessionId: string | null,
  isOffline: boolean,
  sessionLinks: SessionResponse | null,
) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [isSending, setIsSending] = useState(false);
  const [hasOlderMessages, setHasOlderMessages] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  useEffect(() => {
    if (!sessionId) {
      setMessages([WELCOME]);
      setHasOlderMessages(false);
      return;
    }
    if (isOffline) return;

    let cancelled = false;
    listSessionMessages(sessionId, { limit: MESSAGE_WINDOW, anchor: "end" })
      .then((rows) => {
        if (cancelled) return;
        if (rows.length === 0) {
          setMessages([WELCOME]);
          setHasOlderMessages(false);
          return;
        }
        setMessages(rows);
        setHasOlderMessages(rows.length >= MESSAGE_WINDOW);
      })
      .catch(() => {
        if (cancelled) return;
        setMessages([WELCOME]);
        setHasOlderMessages(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, isOffline]);

  const loadOlderMessages = useCallback(async () => {
    if (!sessionId || isOffline || loadingOlder || !hasOlderMessages) return;
    const list = messagesRef.current;
    const first = list.find((m) => m.createdAt);
    if (!first?.createdAt) return;
    setLoadingOlder(true);
    try {
      const older = await listSessionMessages(sessionId, {
        limit: 50,
        before: first.createdAt,
        anchor: "end",
      });
      if (older.length === 0) {
        setHasOlderMessages(false);
        return;
      }
      setHasOlderMessages(older.length >= 50);
      setMessages((prev) => [...older, ...prev]);
    } catch {
      setHasOlderMessages(false);
    } finally {
      setLoadingOlder(false);
    }
  }, [sessionId, isOffline, loadingOlder, hasOlderMessages]);

  const canSend = useMemo(
    () =>
      Boolean(sessionId) &&
      !isOffline &&
      !isSending &&
      requiredLinkIds(sessionLinks) !== null,
    [sessionId, isOffline, isSending, sessionLinks],
  );

  const contextHint = useMemo(() => {
    if (!sessionId || isOffline) return null;
    if (requiredLinkIds(sessionLinks) !== null) return null;
    return SESSION_LINKS_HINT;
  }, [sessionId, isOffline, sessionLinks]);

  const sendMessage = useCallback(
    async (textRaw: string) => {
      const text = textRaw.trim();
      if (!text || !sessionId || isOffline || isSending) return;

      const ids = requiredLinkIds(sessionLinks);
      if (!ids) return;

      setIsSending(true);
      setMessages((prev) => [...prev, { role: "user", content: text }]);

      const streamRef: { current: EventSource | null } = { current: null };
      try {
        const userRow = await postSessionMessage({
          sessionId,
          content: text,
          resume_template_id: ids.resume_template_id,
          resume_id: ids.resume_id,
          job_description_id: ids.job_description_id,
        });

        setMessages((prev) => {
          const copy = [...prev];
          const i = copy.length - 1;
          if (i >= 0 && copy[i].role === "user") {
            copy[i] = apiChatRowToChatMessage(userRow);
          }
          return copy;
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

  return {
    messages,
    isSending,
    canSend,
    sendMessage,
    contextHint,
    loadOlderMessages,
    hasOlderMessages,
    loadingOlder,
  };
}
