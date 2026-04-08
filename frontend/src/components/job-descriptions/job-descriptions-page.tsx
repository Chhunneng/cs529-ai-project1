"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  activateJobDescription,
  createJobDescription,
  getSession,
  listJobDescriptions,
  listSessions,
  pingBackend,
  type JobDescriptionResponse,
  type SessionResponse,
} from "@/lib/api";
import { AppPageHeader } from "@/components/layout/app-page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { listRowClasses } from "@/lib/list-row-styles";
import { SELECT_NONE as NONE, labelSessionSelectValue } from "@/lib/select-display";
import { cn } from "@/lib/utils";

function previewLine(raw: string, max = 100): string {
  const lines = raw.trim().split(/\r?\n/);
  const first = lines.find((l) => l.trim()) ?? raw.trim();
  if (!first) return "—";
  const t = first.trim().slice(0, max);
  return first.trim().length > max ? `${t}…` : t;
}

export function JobDescriptionsPage() {
  const [connection, setConnection] = useState<"checking" | "ready" | "offline">("checking");
  const apiReady = connection === "ready";

  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [sessionId, setSessionId] = useState<string>(NONE);
  const [activeJdId, setActiveJdId] = useState<string | null>(null);

  const [jds, setJds] = useState<JobDescriptionResponse[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingJds, setLoadingJds] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [pasteBusy, setPasteBusy] = useState(false);
  const [pasteError, setPasteError] = useState<string | null>(null);

  const [viewJd, setViewJd] = useState<JobDescriptionResponse | null>(null);
  const [activateBusyId, setActivateBusyId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    pingBackend().then((ok) => {
      if (!cancelled) setConnection(ok ? "ready" : "offline");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadSessions = useCallback(async () => {
    if (!apiReady) return;
    setError(null);
    setLoadingSessions(true);
    try {
      const rows = await listSessions();
      setSessions(rows);
      setSessionId((prev) => (prev !== NONE ? prev : (rows[0]?.id ?? NONE)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load sessions.");
    } finally {
      setLoadingSessions(false);
    }
  }, [apiReady]);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const refreshSessionAndList = useCallback(async () => {
    if (!apiReady || sessionId === NONE) {
      setJds([]);
      setActiveJdId(null);
      return;
    }
    setError(null);
    setLoadingJds(true);
    try {
      const [s, list] = await Promise.all([
        getSession(sessionId),
        listJobDescriptions({ session_id: sessionId, limit: 100 }),
      ]);
      setActiveJdId(s.active_jd_id);
      setJds(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load job postings.");
      setJds([]);
      setActiveJdId(null);
    } finally {
      setLoadingJds(false);
    }
  }, [apiReady, sessionId]);

  useEffect(() => {
    void refreshSessionAndList();
  }, [refreshSessionAndList]);

  async function handlePasteSubmit() {
    if (!apiReady || sessionId === NONE) return;
    const text = pasteText.trim();
    if (!text) {
      setPasteError("Paste the job posting text first.");
      return;
    }
    setPasteError(null);
    setPasteBusy(true);
    try {
      await createJobDescription({ session_id: sessionId, raw_text: text, set_active: true });
      setPasteOpen(false);
      setPasteText("");
      await refreshSessionAndList();
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : "Could not save job posting.");
    } finally {
      setPasteBusy(false);
    }
  }

  async function handleActivate(jdId: string) {
    if (!apiReady || sessionId === NONE || jdId === activeJdId) return;
    setActivateBusyId(jdId);
    setError(null);
    try {
      await activateJobDescription({ session_id: sessionId, job_description_id: jdId });
      const s = await getSession(sessionId);
      setActiveJdId(s.active_jd_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not set active job posting.");
    } finally {
      setActivateBusyId(null);
    }
  }

  const noSession = sessionId === NONE;
  const canPaste = apiReady && !noSession && !pasteBusy;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <AppPageHeader
        title="Job postings"
        description={
          <>
            Choose a chat, then paste postings or pick which one is active for tailoring and PDFs. You can also do
            this from{" "}
            <Link href="/" className="font-medium text-primary underline underline-offset-4">
              Chat
            </Link>
            .
          </>
        }
      />

      <div className="flex flex-col gap-4 p-4 md:p-5">
        {connection === "offline" ? (
          <Alert variant="destructive" className="border-destructive/50">
            <AlertTitle>Can&apos;t reach the server</AlertTitle>
            <AlertDescription>
              Check that the API is running and <code className="text-xs">NEXT_PUBLIC_API_BASE_URL</code> is set
              correctly.
            </AlertDescription>
          </Alert>
        ) : null}

        {error ? (
          <Alert variant="destructive" className="border-destructive/50">
            <AlertTitle>Something went wrong</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-3 border-b border-border/60 bg-muted/15 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 flex-col gap-1">
              <CardTitle className="text-base font-semibold tracking-tight">Session</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                Job text is stored per chat. The active posting is used when you generate a PDF from this session.
              </CardDescription>
            </div>
            <div className="flex shrink-0 flex-row flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!apiReady || loadingSessions}
                onClick={() => void loadSessions()}
              >
                Reload sessions
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 p-4">
            {loadingSessions ? (
              <Skeleton className="h-9 w-full max-w-md" />
            ) : (
              <div className="flex max-w-md flex-col gap-2">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Chat</div>
                <Select
                  value={sessionId}
                  onValueChange={(v) => {
                    setSessionId(v ?? NONE);
                    setError(null);
                  }}
                  disabled={!apiReady}
                >
                  <SelectTrigger className="w-full" size="sm">
                    <SelectValue placeholder="Choose a session…">
                      {(value) => labelSessionSelectValue(value, sessions)}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>No session selected</SelectItem>
                    {sessions.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.id.slice(0, 8)}… ({new Date(s.created_at).toLocaleDateString()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-3 border-b border-border/60 bg-muted/15 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 flex-col gap-1">
              <CardTitle className="text-base font-semibold tracking-tight">Postings for this chat</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                Paste a full job description to save it and set it as active, or activate an older posting.
              </CardDescription>
            </div>
            <div className="flex shrink-0 flex-row flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!apiReady || noSession || loadingJds}
                onClick={() => void refreshSessionAndList()}
              >
                Refresh
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={!canPaste || loadingJds}
                onClick={() => {
                  setPasteError(null);
                  setPasteOpen(true);
                }}
              >
                Paste posting
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 p-4">
            {noSession ? (
              <Empty className="min-h-[140px] border border-dashed border-border/60 bg-muted/10 py-8">
                <EmptyHeader>
                  <EmptyTitle className="font-semibold tracking-tight">Pick a chat</EmptyTitle>
                  <EmptyDescription>
                    Select a session above to see and manage job postings for that conversation.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : loadingJds ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : jds.length === 0 ? (
              <Empty className="min-h-[160px] border border-dashed border-border/60 bg-muted/10 py-8">
                <EmptyHeader>
                  <EmptyTitle className="font-semibold tracking-tight">No postings yet</EmptyTitle>
                  <EmptyDescription>Paste a job description to save it and use it for tailoring.</EmptyDescription>
                </EmptyHeader>
                <Button
                  type="button"
                  size="sm"
                  className="mt-2"
                  disabled={!canPaste}
                  onClick={() => {
                    setPasteError(null);
                    setPasteOpen(true);
                  }}
                >
                  Paste posting
                </Button>
              </Empty>
            ) : (
              <div className="flex flex-col gap-2">
                {jds.map((jd) => {
                  const isActive = activeJdId === jd.id;
                  return (
                    <div
                      key={jd.id}
                      role="row"
                      data-state={isActive ? "selected" : undefined}
                      className={cn(
                        "flex min-h-11 w-full flex-col gap-2 rounded-lg px-3 py-2 sm:flex-row sm:items-center sm:gap-3",
                        listRowClasses(isActive),
                      )}
                    >
                      <button
                        type="button"
                        className="flex min-w-0 flex-1 flex-col items-stretch gap-0.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25 rounded-md -mx-1 px-1"
                        aria-current={isActive ? "true" : undefined}
                        onClick={() => setViewJd(jd)}
                      >
                        <span className="truncate text-sm font-medium leading-snug text-foreground">
                          {previewLine(jd.raw_text)}
                        </span>
                        <span className="font-mono text-[10px] leading-tight text-muted-foreground">
                          {jd.id.slice(0, 8)}… · {new Date(jd.created_at).toLocaleString()}
                        </span>
                      </button>
                      <div className="flex shrink-0 flex-row flex-wrap items-center gap-2 sm:justify-end">
                        {!isActive ? (
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            disabled={!apiReady || activateBusyId === jd.id}
                            onClick={() => void handleActivate(jd.id)}
                          >
                            {activateBusyId === jd.id ? "Setting…" : "Set active"}
                          </Button>
                        ) : (
                          <span className="text-[11px] font-medium text-muted-foreground">Active</span>
                        )}
                        <Button type="button" variant="outline" size="sm" onClick={() => setViewJd(jd)}>
                          View
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog
        open={pasteOpen}
        onOpenChange={(o) => {
          setPasteOpen(o);
          if (!o) {
            setPasteText("");
            setPasteError(null);
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Paste job posting</DialogTitle>
            <DialogDescription>
              The text is saved to this chat and set as the active posting for PDFs and tailoring.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste the full job description here…"
            className="min-h-[200px] resize-y"
            disabled={pasteBusy}
          />
          {pasteError ? <p className="text-sm text-destructive">{pasteError}</p> : null}
          <DialogFooter>
            <Button type="button" variant="outline" disabled={pasteBusy} onClick={() => setPasteOpen(false)}>
              Cancel
            </Button>
            <Button type="button" disabled={!canPaste || pasteBusy} onClick={() => void handlePasteSubmit()}>
              {pasteBusy ? "Saving…" : "Save and set active"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={viewJd != null} onOpenChange={(o) => !o && setViewJd(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Job posting</DialogTitle>
            <DialogDescription className="font-mono text-[11px] break-all">
              {viewJd?.id}
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[min(60vh,420px)] rounded-md border border-border/60 bg-muted/10 p-3">
            <pre className="whitespace-pre-wrap wrap-break-word text-sm leading-relaxed">{viewJd?.raw_text}</pre>
          </ScrollArea>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setViewJd(null)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
