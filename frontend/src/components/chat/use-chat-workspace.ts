"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createSession,
  deleteSession,
  listSessions,
  pingBackend,
  type SessionResponse,
} from "@/lib/api";

const ACTIVE_KEY = "resume-agent:active-session";

function readActive(): string | null {
  try {
    const v = localStorage.getItem(ACTIVE_KEY);
    return v && v.length > 0 ? v : null;
  } catch {
    return null;
  }
}

function writeActive(id: string | null) {
  if (id) localStorage.setItem(ACTIVE_KEY, id);
  else localStorage.removeItem(ACTIVE_KEY);
}

export type ConnectionStatus = "checking" | "ready" | "offline";

export function useChatWorkspace() {
  const [connection, setConnection] = useState<ConnectionStatus>("checking");
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  const refreshSessions = useCallback(async (focusId?: string | null) => {
    setSessionsError(null);
    setSessionsLoading(true);
    try {
      const rows = await listSessions();
      setSessions(rows);
      const ids = rows.map((r) => String(r.id));
      const saved = readActive();
      const next: string | null =
        focusId != null && focusId !== "" && ids.includes(focusId)
          ? focusId
          : saved && ids.includes(saved)
            ? saved
            : ids[0] ?? null;
      setActiveSessionId(next);
      writeActive(next);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load sessions";
      setSessionsError(msg);
      throw e;
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    pingBackend().then((ok) => {
      if (cancelled) return;
      setConnection(ok ? "ready" : "offline");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (connection !== "ready") return;
    let cancelled = false;
    void refreshSessions().catch(() => {
      if (!cancelled) {
        /* error state set in refreshSessions */
      }
    });
    return () => {
      cancelled = true;
    };
  }, [connection, refreshSessions]);

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id);
    writeActive(id);
  }, []);

  const createNewChat = useCallback(async () => {
    if (connection !== "ready") throw new Error("API unavailable");
    const { id } = await createSession();
    await refreshSessions(id);
  }, [connection, refreshSessions]);

  const removeSession = useCallback(
    async (id: string) => {
      if (connection !== "ready") throw new Error("API unavailable");
      const previousActive = activeSessionId;
      await deleteSession(id);
      if (previousActive === id) {
        writeActive(null);
      }
      await refreshSessions(previousActive === id ? undefined : (previousActive ?? undefined));
    },
    [connection, activeSessionId, refreshSessions],
  );

  const retryConnection = useCallback(() => {
    setConnection("checking");
    pingBackend().then((ok) => setConnection(ok ? "ready" : "offline"));
  }, []);

  return {
    connection,
    sessions,
    activeSessionId,
    selectSession,
    createNewChat,
    removeSession,
    retryConnection,
    retryLoadSessions: () => void refreshSessions().catch(() => undefined),
    sessionsLoading,
    sessionsError,
    isOffline: connection === "offline",
    isChecking: connection === "checking",
    isReady: connection === "ready",
  };
}
