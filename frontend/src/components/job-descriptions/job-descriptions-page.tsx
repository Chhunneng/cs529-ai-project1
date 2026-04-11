"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { VirtualList } from "@/components/lists/virtual-list";

import {
  createJobDescriptionLibrary,
  listJobDescriptions,
  pingBackend,
  type JobDescriptionResponse,
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
import { Skeleton } from "@/components/ui/skeleton";
import { listRowClasses } from "@/lib/list-row-styles";
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

  const [jds, setJds] = useState<JobDescriptionResponse[]>([]);
  const [loadingJds, setLoadingJds] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [pasteBusy, setPasteBusy] = useState(false);
  const [pasteError, setPasteError] = useState<string | null>(null);

  const [viewJd, setViewJd] = useState<JobDescriptionResponse | null>(null);

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
    setLoadingJds(true);
    try {
      const list = await listJobDescriptions({ limit: 200, offset: 0 });
      setJds(list.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load job postings.");
      setJds([]);
    } finally {
      setLoadingJds(false);
    }
  }, [apiReady]);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

  async function handlePasteSubmit() {
    if (!apiReady) return;
    const text = pasteText.trim();
    if (!text) {
      setPasteError("Paste the job posting text first.");
      return;
    }
    setPasteError(null);
    setPasteBusy(true);
    try {
      await createJobDescriptionLibrary(text);
      setPasteOpen(false);
      setPasteText("");
      await refreshData();
    } catch (e) {
      setPasteError(e instanceof Error ? e.message : "Could not save job posting.");
    } finally {
      setPasteBusy(false);
    }
  }

  const canPaste = apiReady && !pasteBusy;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <AppPageHeader
        title="Job postings"
        description="Saved job descriptions live in a shared library. Paste text to add a new posting, or open one to read the full text."
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
              <CardTitle className="text-base font-semibold tracking-tight">All job postings</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                Browse saved postings. To use one in a conversation, open{" "}
                <Link href="/" className="font-medium text-primary underline underline-offset-4">
                  Chat
                </Link>{" "}
                and pick it in Session tools.
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
            {loadingJds ? (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : jds.length === 0 ? (
              <Empty className="min-h-[160px] border border-dashed border-border/60 bg-muted/10 py-8">
                <EmptyHeader>
                  <EmptyTitle className="font-semibold tracking-tight">No postings yet</EmptyTitle>
                  <EmptyDescription>Paste a job description to save it to the shared library.</EmptyDescription>
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
              <VirtualList items={jds} estimateSize={76} maxHeight="min(65vh,560px)">
                {(jd) => (
                  <div className="px-0.5 pb-1">
                    <div
                      role="row"
                      className={cn(
                        "flex min-h-11 w-full flex-col gap-2 rounded-lg px-3 py-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3",
                        listRowClasses(false),
                      )}
                    >
                      <button
                        type="button"
                        className="flex min-w-0 flex-1 flex-col items-stretch gap-0.5 rounded-md px-1 text-left -mx-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25"
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
                        <Button type="button" variant="outline" size="sm" onClick={() => setViewJd(jd)}>
                          View
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </VirtualList>
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
        description="Saves the text to the shared library. You can attach it to a chat later from Session tools."
        value={pasteText}
        onValueChange={setPasteText}
        error={pasteError}
        confirmLabel="Save posting"
        confirmBusyLabel="Saving…"
        onConfirm={handlePasteSubmit}
        isSubmitting={pasteBusy}
        confirmDisabled={!apiReady}
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
            <pre className="max-w-prose whitespace-pre-wrap wrap-break-word text-sm leading-relaxed">
              {viewJd?.raw_text}
            </pre>
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
