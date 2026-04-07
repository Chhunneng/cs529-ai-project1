"use client";

import { useCallback, useEffect, useState } from "react";

import { pingBackend } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useResumes } from "@/components/resumes/use-resumes";

export function ResumeDashboard() {
  const [connection, setConnection] = useState<"checking" | "ready" | "offline">("checking");
  const apiReady = connection === "ready";

  const { items, loading, error, refresh, createStub } = useResumes(apiReady);

  const [addOpen, setAddOpen] = useState(false);
  const [filename, setFilename] = useState("resume.pdf");
  const [actionError, setActionError] = useState<string | null>(null);

  const checkConnection = useCallback(async () => {
    setConnection("checking");
    const ok = await pingBackend();
    setConnection(ok ? "ready" : "offline");
  }, []);

  async function handleCreate() {
    setActionError(null);
    try {
      await createStub(filename.trim() || "resume.pdf");
      setAddOpen(false);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not create resume.");
    }
  }

  useEffect(() => {
    // Let the effect subscribe; actual state updates happen asynchronously.
    const t = setTimeout(() => void checkConnection(), 0);
    return () => clearTimeout(t);
  }, [checkConnection]);

  return (
    <div className="flex h-full w-full flex-col gap-5 p-4 md:p-5">
      {connection === "offline" ? (
        <Alert variant="destructive" className="border-destructive/50">
          <AlertTitle>Backend unreachable</AlertTitle>
          <AlertDescription className="flex flex-col gap-2">
            <span>Check NEXT_PUBLIC_API_BASE_URL and that the API is running.</span>
            <Button className="w-fit" size="sm" variant="outline" onClick={() => void checkConnection()}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive" className="border-destructive/50">
          <AlertTitle>Could not load resumes</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
        <CardHeader className="flex flex-row items-start justify-between gap-3 border-b border-border/60 bg-muted/15">
          <div className="space-y-1">
            <CardTitle className="text-base font-semibold tracking-tight">Resumes</CardTitle>
            <CardDescription className="text-sm leading-relaxed">
              Manage the resume records stored in the API (Phase 1: metadata + parsed JSON if available).
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={!apiReady}
              onClick={() => setAddOpen(true)}
            >
              Add stub
            </Button>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={!apiReady || loading}
              onClick={() => void refresh()}
            >
              Refresh
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-4">
          {loading ? (
            <div className="grid gap-3 md:grid-cols-2">
              <Skeleton className="h-20 w-full rounded-xl" />
              <Skeleton className="h-20 w-full rounded-xl" />
            </div>
          ) : items.length === 0 ? (
            <Empty className="min-h-[220px] border-none bg-muted/15 py-10">
              <EmptyHeader>
                <EmptyTitle className="font-semibold tracking-tight">No resumes yet</EmptyTitle>
                <EmptyDescription className="max-w-sm opacity-90">
                  Create a stub to start. Later phases can support uploading and parsing.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {items.map((r) => (
                <div
                  key={r.id}
                  className="flex flex-col gap-2 rounded-xl border border-border/80 bg-muted/10 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="break-all font-mono text-[11px] leading-snug text-foreground">
                        {r.id}
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        Created {new Date(r.created_at).toLocaleString()}
                      </div>
                    </div>
                    <Badge variant={r.openai_file_id ? "default" : "secondary"}>
                      {r.openai_file_id ? "file-linked" : "stub"}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create resume record</DialogTitle>
            <DialogDescription>Phase 1 stores metadata only. Enter a display filename.</DialogDescription>
          </DialogHeader>
          {actionError ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Create failed</AlertTitle>
              <AlertDescription>{actionError}</AlertDescription>
            </Alert>
          ) : null}
          <div className="flex flex-col gap-2">
            <Input value={filename} onChange={(e) => setFilename(e.target.value)} placeholder="resume.pdf" />
          </div>
          <DialogFooter className="flex flex-row gap-2 sm:justify-end">
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!apiReady} onClick={() => void handleCreate()}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

