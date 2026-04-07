"use client";

import { useCallback, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";

import { createResume, deleteResume, listResumes, pingBackend, type ResumeListItem } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

function shortId(id: string) {
  return `${id.slice(0, 8)}…`;
}

export function ResumesPage() {
  const [connection, setConnection] = useState<"checking" | "ready" | "offline">("checking");
  const apiReady = connection === "ready";
  const [items, setItems] = useState<ResumeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [filename, setFilename] = useState("resume.pdf");
  const [actionError, setActionError] = useState<string | null>(null);

  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!apiReady) return;
    setError(null);
    setLoading(true);
    try {
      const rows = await listResumes();
      setItems(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load your resumes.");
    } finally {
      setLoading(false);
    }
  }, [apiReady]);

  useEffect(() => {
    let cancelled = false;
    pingBackend().then((ok) => {
      if (!cancelled) setConnection(ok ? "ready" : "offline");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleCreate() {
    setActionError(null);
    if (!apiReady || !filename.trim()) return;
    try {
      await createResume(filename.trim());
      setAddOpen(false);
      setFilename("resume.pdf");
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not create resume.");
    }
  }

  async function confirmDelete() {
    if (!pendingDeleteId) return;
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await deleteResume(pendingDeleteId);
      setPendingDeleteId(null);
      await refresh();
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : "Could not delete resume.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <header className="shrink-0 border-b border-border/80 bg-card/40 px-4 py-3 backdrop-blur-sm md:px-5">
        <h1 className="text-base font-semibold tracking-tight text-foreground md:text-lg">Your resumes</h1>
        <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
          Create a draft resume to link in chat, or attach a file later. You can remove drafts you no longer need.
        </p>
      </header>

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
            <AlertTitle>Could not load resumes</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 border-b border-border/60 bg-muted/15">
            <div className="flex flex-col gap-1">
              <CardTitle className="text-base font-semibold tracking-tight">All resumes</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                Each resume has an ID you can link to a chat. Deleting a resume clears it from any chat that used it.
              </CardDescription>
            </div>
            <div className="flex flex-row flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!apiReady}
                onClick={() => setAddOpen(true)}
              >
                New resume
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
              <div className="flex flex-col gap-3 md:grid md:grid-cols-2">
                <Skeleton className="h-24 w-full rounded-xl" />
                <Skeleton className="h-24 w-full rounded-xl" />
              </div>
            ) : items.length === 0 ? (
              <Empty className="min-h-[220px] border-none bg-muted/15 py-10">
                <EmptyHeader>
                  <EmptyTitle className="font-semibold tracking-tight">No resumes yet</EmptyTitle>
                  <EmptyDescription className="max-w-sm opacity-90">
                    Create a draft to get started. You can also add one from the Chat screen&apos;s workspace panel.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <div className="flex flex-col gap-3 md:grid md:grid-cols-2">
                {items.map((r) => (
                  <div
                    key={r.id}
                    className="flex flex-col gap-3 rounded-xl border border-border/80 bg-muted/10 p-3"
                  >
                    <div className="flex flex-row items-start justify-between gap-2">
                      <div className="min-w-0 flex flex-col gap-1">
                        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                          Resume ID
                        </span>
                        <span className="break-all font-mono text-xs leading-snug text-foreground" title={r.id}>
                          {r.id}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Added {new Date(r.created_at).toLocaleString()}
                        </span>
                      </div>
                      <Badge variant={r.openai_file_id ? "default" : "secondary"}>
                        {r.openai_file_id ? "File attached" : "Draft"}
                      </Badge>
                    </div>
                    <div className="flex flex-row items-center justify-end border-t border-border/60 pt-2">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                        disabled={!apiReady || isDeleting}
                        aria-label={`Delete resume ${shortId(r.id)}`}
                        onClick={() => {
                          setDeleteError(null);
                          setPendingDeleteId(r.id);
                        }}
                      >
                        <Trash2 className="size-4" strokeWidth={2} />
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New resume</DialogTitle>
            <DialogDescription>
              Give this draft a filename for your reference. You can link it from Chat when you&apos;re ready.
            </DialogDescription>
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

      <Dialog
        open={pendingDeleteId != null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDeleteId(null);
            setDeleteError(null);
          }
        }}
      >
        <DialogContent showCloseButton className="gap-0 sm:max-w-md">
          <DialogHeader className="space-y-2 pr-8 text-left">
            <DialogTitle className="leading-snug">Delete this resume?</DialogTitle>
            <DialogDescription>
              This removes the resume record. Chats that linked to it will no longer have a resume selected. This
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteError ? (
            <p className="mt-3 text-sm leading-relaxed text-destructive">{deleteError}</p>
          ) : null}
          <div className="mt-4 flex flex-col-reverse gap-2 border-t border-border/70 pt-3 sm:flex-row sm:justify-end sm:gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={isDeleting}
              className="w-full sm:w-auto"
              onClick={() => {
                setPendingDeleteId(null);
                setDeleteError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={isDeleting}
              className="w-full font-medium sm:w-auto"
              onClick={() => void confirmDelete()}
            >
              {isDeleting ? "Deleting…" : "Delete resume"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
