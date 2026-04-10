"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

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

export type ChatWorkspaceValue = {
  connection: ConnectionStatus;
  sessions: SessionResponse[];
  activeSessionId: string | null;
  selectSession: (id: string) => void;
  createNewChat: () => Promise<void>;
  removeSession: (id: string) => Promise<void>;
  /** Merge a session row from getSession/patch so chat sees up-to-date link IDs. */
  upsertSession: (session: SessionResponse) => void;
  retryConnection: () => void;
  retryLoadSessions: () => void;
  loadMoreSessions: () => Promise<void>;
  sessionsTotal: number;
  sessionsLoadingMore: boolean;
  sessionsLoading: boolean;
  sessionsError: string | null;
  isOffline: boolean;
  isChecking: boolean;
  isReady: boolean;
};

const ChatWorkspaceContext = createContext<ChatWorkspaceValue | null>(null);

function useChatWorkspaceState(): ChatWorkspaceValue {
  const [connection, setConnection] = useState<ConnectionStatus>("checking");
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionsLoadingMore, setSessionsLoadingMore] = useState(false);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  const SESSION_PAGE = 100;

  const refreshSessions = useCallback(async (focusId?: string | null) => {
    setSessionsError(null);
    setSessionsLoading(true);
    try {
      const page = await listSessions({ limit: SESSION_PAGE, offset: 0 });
      setSessions(page.items);
      setSessionsTotal(page.total);
      const rows = page.items;
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

  const loadMoreSessions = useCallback(async () => {
    if (connection !== "ready" || sessionsLoading || sessionsLoadingMore) return;
    if (sessions.length >= sessionsTotal) return;
    setSessionsLoadingMore(true);
    try {
      const next = await listSessions({ limit: SESSION_PAGE, offset: sessions.length });
      setSessions((prev) => [...prev, ...next.items]);
      setSessionsTotal(next.total);
    } catch {
      /* ignore */
    } finally {
      setSessionsLoadingMore(false);
    }
  }, [
    connection,
    sessions.length,
    sessionsLoading,
    sessionsLoadingMore,
    sessionsTotal,
  ]);

  const upsertSession = useCallback((session: SessionResponse) => {
    const id = String(session.id);
    setSessions((prev) => {
      const idx = prev.findIndex((x) => String(x.id) === id);
      if (idx === -1) return [...prev, session];
      const next = [...prev];
      next[idx] = session;
      return next;
    });
  }, []);

  return {
    connection,
    sessions,
    activeSessionId,
    selectSession,
    createNewChat,
    removeSession,
    upsertSession,
    retryConnection,
    retryLoadSessions: () => void refreshSessions().catch(() => undefined),
    loadMoreSessions,
    sessionsTotal,
    sessionsLoadingMore,
    sessionsLoading,
    sessionsError,
    isOffline: connection === "offline",
    isChecking: connection === "checking",
    isReady: connection === "ready",
  };
}

export function ChatWorkspaceProvider({ children }: { children: React.ReactNode }) {
  const value = useChatWorkspaceState();
  return <ChatWorkspaceContext.Provider value={value}>{children}</ChatWorkspaceContext.Provider>;
}

export function useChatWorkspace(): ChatWorkspaceValue {
  const ctx = useContext(ChatWorkspaceContext);
  if (!ctx) {
    throw new Error("useChatWorkspace must be used within ChatWorkspaceProvider");
  }
  return ctx;
}
