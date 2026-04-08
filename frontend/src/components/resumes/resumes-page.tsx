"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Braces, Download, Trash2 } from "lucide-react";

import {
  deleteResume,
  downloadResumeFile,
  listResumes,
  pingBackend,
  uploadResume,
  type ResumeListItem,
} from "@/lib/api";
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
import { Skeleton } from "@/components/ui/skeleton";

function shortId(id: string) {
  return `${id.slice(0, 8)}…`;
}

function formatBytes(n: number | null | undefined): string {
  if (n == null || n < 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function ResumesPage() {
  const [connection, setConnection] = useState<"checking" | "ready" | "offline">("checking");
  const apiReady = connection === "ready";
  const [items, setItems] = useState<ResumeListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pickedName, setPickedName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [jsonViewResume, setJsonViewResume] = useState<ResumeListItem | null>(null);

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

  function onPickFile() {
    setActionError(null);
    fileInputRef.current?.click();
  }

  function onFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    setPickedName(f ? f.name : null);
    setActionError(null);
  }

  async function handleUpload() {
    setActionError(null);
    const f = fileInputRef.current?.files?.[0];
    if (!apiReady || !f) {
      setActionError("Choose a PDF, TXT, or DOCX file first.");
      return;
    }
    setUploading(true);
    try {
      await uploadResume(f);
      setAddOpen(false);
      setPickedName(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not upload resume.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(r: ResumeListItem) {
    if (!r.has_file) return;
    setDownloadingId(r.id);
    try {
      await downloadResumeFile(r.id, r.original_filename || "resume");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setDownloadingId(null);
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
          Upload a resume (PDF, TXT, or DOCX). The text is saved for chat context, and you can download your file
          anytime.
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
            <AlertTitle>Something went wrong</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3 border-b border-border/60 bg-muted/15">
            <div className="flex flex-col gap-1">
              <CardTitle className="text-base font-semibold tracking-tight">All resumes</CardTitle>
              <CardDescription className="text-sm leading-relaxed">
                Each resume has an ID you can link to a chat. Deleting a resume removes the stored file and database
                record.
              </CardDescription>
            </div>
            <div className="flex flex-row flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!apiReady}
                onClick={() => {
                  setActionError(null);
                  setPickedName(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                  setAddOpen(true);
                }}
              >
                Upload resume
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
                    Upload a file to get started. You can also add one from the Chat workspace panel.
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
                          {r.original_filename || "Resume"}
                        </span>
                        <span className="break-all font-mono text-xs leading-snug text-foreground" title={r.id}>
                          {r.id}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          Added {new Date(r.created_at).toLocaleString()} · {formatBytes(r.byte_size)}
                        </span>
                      </div>
                      <Badge
                        variant={
                          r.parse_pending ? "secondary" : r.has_file ? "default" : "secondary"
                        }
                      >
                        {r.parse_pending
                          ? "Parsing…"
                          : r.has_file
                            ? "File stored"
                            : "No file"}
                      </Badge>
                    </div>
                    <div className="flex flex-row flex-wrap items-center justify-end gap-2 border-t border-border/60 pt-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={!apiReady || r.parsed_json == null}
                        onClick={() => setJsonViewResume(r)}
                        aria-label={`View parsed JSON for ${shortId(r.id)}`}
                      >
                        <Braces className="size-4" strokeWidth={2} />
                        Parsed JSON
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={!apiReady || !r.has_file || downloadingId === r.id}
                        onClick={() => void handleDownload(r)}
                      >
                        <Download className="size-4" strokeWidth={2} />
                        {downloadingId === r.id ? "Downloading…" : "Download"}
                      </Button>
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

      <Dialog open={jsonViewResume != null} onOpenChange={(open) => !open && setJsonViewResume(null)}>
        <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col gap-0 p-0 sm:max-w-2xl">
          <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-4 text-left">
            <DialogTitle>Parsed resume data</DialogTitle>
            <DialogDescription className="font-mono text-xs">
              {jsonViewResume?.original_filename ?? "Resume"} · {jsonViewResume?.id.slice(0, 8)}…
            </DialogDescription>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-auto px-6 py-3">
            <pre className="whitespace-pre-wrap break-words rounded-lg border border-border/80 bg-muted/30 p-3 font-mono text-[11px] leading-relaxed text-foreground">
              {jsonViewResume?.parsed_json != null
                ? JSON.stringify(jsonViewResume.parsed_json, null, 2)
                : ""}
            </pre>
          </div>
          <DialogFooter className="shrink-0 border-t border-border/70 px-6 py-3 sm:justify-end">
            <Button type="button" variant="outline" onClick={() => setJsonViewResume(null)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={addOpen}
        onOpenChange={(open) => {
          setAddOpen(open);
          if (!open) {
            setActionError(null);
            setPickedName(null);
            if (fileInputRef.current) fileInputRef.current.value = "";
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload resume</DialogTitle>
            <DialogDescription>
              Choose a PDF, plain text (.txt), or Word document (.docx). The server saves the file and extracted text.
            </DialogDescription>
          </DialogHeader>
          {actionError ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Upload failed</AlertTitle>
              <AlertDescription>{actionError}</AlertDescription>
            </Alert>
          ) : null}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={onFileChosen}
          />
          <div className="flex flex-col gap-2">
            <Button type="button" variant="outline" onClick={onPickFile} disabled={!apiReady || uploading}>
              {pickedName ? "Change file" : "Choose file"}
            </Button>
            {pickedName ? (
              <p className="text-sm text-muted-foreground">
                Selected: <span className="font-medium text-foreground">{pickedName}</span>
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">No file selected yet.</p>
            )}
          </div>
          <DialogFooter className="flex flex-row gap-2 sm:justify-end">
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={uploading}>
              Cancel
            </Button>
            <Button disabled={!apiReady || uploading || !pickedName} onClick={() => void handleUpload()}>
              {uploading ? "Uploading…" : "Upload"}
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
              This removes the resume record and deletes the stored file. Chats that linked to it will no longer have a
              resume selected. This cannot be undone.
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
