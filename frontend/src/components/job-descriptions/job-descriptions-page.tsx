"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  activateJobDescription,
  createJobDescription,
  listJobDescriptions,
  listSessions,
  pingBackend,
  type JobDescriptionResponse,
  type SessionResponse,
} from "@/lib/api";
import { AppPageHeader } from "@/components/layout/app-page-header";
import { PasteJobDescriptionDialog } from "@/components/job-descriptions/paste-job-description-dialog";
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
import { listRowClasses } from "@/lib/list-row-styles";
import {
  JD_FILTER_ALL,
  SELECT_NONE as NONE,
  labelJdListFilterValue,
  labelSessionSelectValue,
} from "@/lib/select-display";
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
  const [filterSessionId, setFilterSessionId] = useState<string>(JD_FILTER_ALL);

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

  const activeJdId = useMemo(() => {
    if (sessionId === NONE) return null;
    return sessions.find((s) => s.id === sessionId)?.job_description_id ?? null;
  }, [sessions, sessionId]);

  const displayedJds = useMemo(() => {
    if (filterSessionId === JD_FILTER_ALL) return jds;
    const aid = sessions.find((s) => s.id === filterSessionId)?.job_description_id;
    if (!aid) return [];
    const jd = jds.find((j) => j.id === aid);
    return jd ? [jd] : [];
  }, [jds, sessions, filterSessionId]);

  useEffect(() => {
    let cancelled = false;
    pingBackend().then((ok) => {
      if (!cancelled) setConnection(ok ? "ready" : "offline");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshData = useCallback(async () => {
    if (!apiReady) return;
    setError(null);
    setLoadingSessions(true);
    setLoadingJds(true);
    try {
      const [rows, list] = await Promise.all([
        listSessions(),
        listJobDescriptions({ limit: 200 }),
      ]);
      setSessions(rows);
      setJds(list);
      setSessionId((prev) => (prev !== NONE ? prev : (rows[0]?.id ?? NONE)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load sessions or job postings.");
      setJds([]);
      setSessions([]);
    } finally {
      setLoadingSessions(false);
      setLoadingJds(false);
    }
  }, [apiReady]);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

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
      await refreshData();
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
      await refreshData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not set active job posting.");
    } finally {
      setActivateBusyId(null);
    }
  }

  const noSession = sessionId === NONE;
  const canPaste = apiReady && !noSession && !pasteBusy;
  const filterIsAll = filterSessionId === JD_FILTER_ALL;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <AppPageHeader
        title="Job postings"
        description={
          <>
            Postings are shared across the app. Pick a chat to paste a new posting or set which one is{" "}
            <strong className="font-medium">active</strong> for that conversation (tailoring and PDFs). Use{" "}
            <strong className="font-medium">Show</strong> to narrow the list to the active posting for a specific
            chat. You can also manage this from{" "}
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
              <CardTitle className="text-base font-semibold tracking-tight">Working chat</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                Paste posting and &quot;Set active&quot; apply to this chat. The active posting is used for that
                conversation when you generate a PDF or tailor from Chat.
              </CardDescription>
            </div>
            <div className="flex shrink-0 flex-row flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!apiReady || loadingSessions || loadingJds}
                onClick={() => void refreshData()}
              >
                Reload sessions &amp; list
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 p-4">
            {loadingSessions && sessions.length === 0 ? (
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
            {noSession ? (
              <p className="text-sm text-muted-foreground">
                Select a chat above to enable <strong className="font-medium text-foreground">Paste posting</strong>{" "}
                and <strong className="font-medium text-foreground">Set active</strong> for that conversation.
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-3 border-b border-border/60 bg-muted/15 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 flex-col gap-1">
              <CardTitle className="text-base font-semibold tracking-tight">All job postings</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                Browse every saved posting. Use <strong className="font-medium">Show</strong> to list only the posting
                currently active for a given chat.
              </CardDescription>
            </div>
            <div className="flex shrink-0 flex-row flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!apiReady || loadingJds}
                onClick={() => void refreshData()}
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
          <CardContent className="flex flex-col gap-4 p-4">
            <div className="flex max-w-md flex-col gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Show</div>
              <Select
                value={filterSessionId}
                onValueChange={(v) => setFilterSessionId(v ?? JD_FILTER_ALL)}
                disabled={!apiReady || loadingSessions}
              >
                <SelectTrigger className="w-full" size="sm">
                  <SelectValue>
                    {(value) => labelJdListFilterValue(value, sessions)}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={JD_FILTER_ALL}>All postings</SelectItem>
                  {sessions.map((s) => (
                    <SelectItem key={`filter-${s.id}`} value={s.id}>
                      Active in {s.id.slice(0, 8)}… ({new Date(s.created_at).toLocaleDateString()})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {loadingJds ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : jds.length === 0 ? (
              <Empty className="min-h-[160px] border border-dashed border-border/60 bg-muted/10 py-8">
                <EmptyHeader>
                  <EmptyTitle className="font-semibold tracking-tight">No postings yet</EmptyTitle>
                  <EmptyDescription>
                    Paste a job description (with a chat selected) to save it to the shared library.
                  </EmptyDescription>
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
            ) : !filterIsAll && displayedJds.length === 0 ? (
              <Empty className="min-h-[140px] border border-dashed border-border/60 bg-muted/10 py-8">
                <EmptyHeader>
                  <EmptyTitle className="font-semibold tracking-tight">No active posting for this chat</EmptyTitle>
                  <EmptyDescription>
                    That chat does not have an active job posting yet. Choose another filter or set one active from the
                    list.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <div className="flex flex-col gap-2">
                {displayedJds.map((jd) => {
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
                            disabled={!apiReady || noSession || activateBusyId === jd.id}
                            onClick={() => void handleActivate(jd.id)}
                          >
                            {activateBusyId === jd.id ? "Setting…" : "Set active"}
                          </Button>
                        ) : (
                          <span className="text-[11px] font-medium text-muted-foreground">Active for this chat</span>
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

      <PasteJobDescriptionDialog
        open={pasteOpen}
        onOpenChange={(o) => {
          setPasteOpen(o);
          if (!o) {
            setPasteText("");
            setPasteError(null);
          }
        }}
        title="Paste job posting"
        description={
          <>
            Saves the text to the shared library and sets it as the active posting for your selected chat (for PDFs
            and tailoring).
          </>
        }
        value={pasteText}
        onValueChange={setPasteText}
        error={pasteError}
        confirmLabel="Save and set active"
        confirmBusyLabel="Saving…"
        onConfirm={handlePasteSubmit}
        isSubmitting={pasteBusy}
        confirmDisabled={!apiReady || noSession}
      />

      <Dialog open={viewJd != null} onOpenChange={(o) => !o && setViewJd(null)}>
        <DialogContent className="w-full max-w-4xl sm:max-w-4xl">
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
