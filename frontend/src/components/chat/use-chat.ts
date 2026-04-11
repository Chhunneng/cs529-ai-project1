"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ChatMessage } from "@/components/chat/types";
import {
  apiChatRowToChatMessage,
  getSessionPendingReplies,
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
const POLL_MS = 2500;

function getIncompleteUserMessageIds(messages: ChatMessage[]): string[] {
  const ids: string[] = [];
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (m.role !== "user" || !m.id) continue;
    const next = messages[i + 1];
    if (!next || next.role !== "assistant") {
      ids.push(m.id);
    }
  }
  return ids;
}

function mergePendingFromServer(messages: ChatMessage[], serverIds: string[]): string[] {
  const incomplete = new Set(getIncompleteUserMessageIds(messages));
  return serverIds.filter((id) => incomplete.has(id));
}

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
  const [pendingReplyUserIds, setPendingReplyUserIds] = useState<string[]>([]);
  const [hasOlderMessages, setHasOlderMessages] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  useEffect(() => {
    if (!sessionId) {
      setMessages([WELCOME]);
      setHasOlderMessages(false);
      setPendingReplyUserIds([]);
      return;
    }
    if (isOffline) return;

    let cancelled = false;
    (async () => {
      try {
        const [rows, pending] = await Promise.all([
          listSessionMessages(sessionId, { limit: MESSAGE_WINDOW, anchor: "end" }),
          getSessionPendingReplies(sessionId).catch(() => ({
            pending_user_message_ids: [] as string[],
          })),
        ]);
        if (cancelled) return;
        if (rows.length === 0) {
          setMessages([WELCOME]);
          setHasOlderMessages(false);
          setPendingReplyUserIds([]);
          return;
        }
        setMessages(rows);
        setHasOlderMessages(rows.length >= MESSAGE_WINDOW);
        setPendingReplyUserIds(
          mergePendingFromServer(rows, pending.pending_user_message_ids ?? []),
        );
      } catch {
        if (cancelled) return;
        setMessages([WELCOME]);
        setHasOlderMessages(false);
        setPendingReplyUserIds([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sessionId, isOffline]);

  const pendingKey = pendingReplyUserIds.slice().sort().join(",");

  useEffect(() => {
    if (!sessionId || isOffline || pendingReplyUserIds.length === 0) return;

    const t = window.setInterval(() => {
      void (async () => {
        try {
          const [rows, pending] = await Promise.all([
            listSessionMessages(sessionId, { limit: MESSAGE_WINDOW, anchor: "end" }),
            getSessionPendingReplies(sessionId).catch(() => ({
              pending_user_message_ids: [] as string[],
            })),
          ]);
          setMessages(rows);
          setHasOlderMessages(rows.length >= MESSAGE_WINDOW);
          setPendingReplyUserIds(
            mergePendingFromServer(rows, pending.pending_user_message_ids ?? []),
          );
        } catch {
          /* ignore transient poll errors */
        }
      })();
    }, POLL_MS);

    return () => window.clearInterval(t);
  }, [sessionId, isOffline, pendingKey]);

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
      let userRow: ApiChatRow | null = null;
      try {
        userRow = await postSessionMessage({
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
            copy[i] = apiChatRowToChatMessage(userRow!);
          }
          return copy;
        });

        setPendingReplyUserIds((prev) =>
          prev.includes(userRow!.id) ? prev : [...prev, userRow!.id],
        );

        await new Promise<void>((resolve) => {
          streamRef.current = openAssistantReplyStream(sessionId, userRow!.id, {
            onEvent: (ev) => {
              if (ev.type === "assistant") {
                const row = ev.message as ApiChatRow;
                setMessages((prev) => [...prev, apiChatRowToChatMessage(row)]);
                setPendingReplyUserIds((prev) => prev.filter((x) => x !== userRow!.id));
                resolve();
                return;
              }
              if (ev.type === "timeout") {
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
              setPendingReplyUserIds((prev) => prev.filter((x) => x !== userRow!.id));
              resolve();
            },
            onTransportError: () => {
              resolve();
            },
          });
        });
      } catch {
        setMessages((prev) => {
          const copy = [...prev];
          if (
            copy.length > 0 &&
            copy[copy.length - 1].role === "user" &&
            !copy[copy.length - 1].id
          ) {
            copy.pop();
          }
          return [
            ...copy,
            {
              role: "assistant",
              content:
                "Could not send your message or open the reply stream. Check the API URL, CORS, and backend logs.",
            },
          ];
        });
        if (userRow) {
          setPendingReplyUserIds((prev) => prev.filter((x) => x !== userRow!.id));
        }
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
    pendingReplyUserIds,
    canSend,
    sendMessage,
    contextHint,
    loadOlderMessages,
    hasOlderMessages,
    loadingOlder,
  };
}
