"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Braces, Download, Trash2 } from "lucide-react";

import {
  createJobDescription,
  createResumeOutput,
  deleteResume,
  downloadResumeFile,
  getResumeOutput,
  getSession,
  listJobDescriptions,
  listResumes,
  listResumeTemplates,
  patchSession,
  uploadResume,
  resumeOutputPdfUrl,
  type JobDescriptionResponse,
  type ResumeListItem,
  type ResumeOutputResponse,
  type ResumeTemplateListItem,
  type SessionResponse,
} from "@/lib/api";
import { PasteJobDescriptionDialog } from "@/components/job-descriptions/paste-job-description-dialog";
import { TemplateManagerSheet } from "@/components/templates/template-manager-sheet";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  SELECT_NONE as NONE,
  SELECT_NONE_JOB as JD_NONE,
  labelJobSelectValue,
  labelResumeSelectValue,
  labelTemplateSelectValue,
} from "@/lib/select-display";
import { listRowClasses } from "@/lib/list-row-styles";
import { cn } from "@/lib/utils";

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

function ContextPanelOuter({
  variant,
  className,
  children,
}: {
  variant: "sidebar" | "embedded";
  className?: string;
  children: React.ReactNode;
}) {
  if (variant === "embedded") {
    return <div className={className}>{children}</div>;
  }
  return <aside className={className}>{children}</aside>;
}

export function ContextPanel({
  sessionId,
  apiReady,
  variant = "sidebar",
}: {
  sessionId: string | null;
  apiReady: boolean;
  variant?: "sidebar" | "embedded";
}) {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [templates, setTemplates] = useState<ResumeTemplateListItem[]>([]);
  const [templateId, setTemplateId] = useState<string>("");
  const [resumeValue, setResumeValue] = useState<string>(NONE);
  const [jds, setJds] = useState<JobDescriptionResponse[]>([]);
  const [jdValue, setJdValue] = useState<string>(JD_NONE);
  const [listsLoading, setListsLoading] = useState(true);
  const [lastOutput, setLastOutput] = useState<ResumeOutputResponse | null>(null);
  const [outputBusy, setOutputBusy] = useState(false);
  const [outputNotice, setOutputNotice] = useState<string | null>(null);
  const [templateManagerOpen, setTemplateManagerOpen] = useState(false);
  const [pendingDeleteResumeId, setPendingDeleteResumeId] = useState<string | null>(null);
  const [isDeletingResume, setIsDeletingResume] = useState(false);
  const [deleteResumeError, setDeleteResumeError] = useState<string | null>(null);

  const [addOpen, setAddOpen] = useState(false);
  const resumeFileRef = useRef<HTMLInputElement>(null);
  const [resumePickLabel, setResumePickLabel] = useState<string | null>(null);
  const [resumeUploadBusy, setResumeUploadBusy] = useState(false);
  const [resumeDownloadBusy, setResumeDownloadBusy] = useState<string | null>(null);
  const [resumeJsonView, setResumeJsonView] = useState<ResumeListItem | null>(null);
  const [jdOpen, setJdOpen] = useState(false);
  const [jdDraft, setJdDraft] = useState("");
  const [jdPasteBusy, setJdPasteBusy] = useState(false);
  const [jdPasteError, setJdPasteError] = useState<string | null>(null);

  const loadLists = useCallback(async () => {
    if (!apiReady) return;
    setListsLoading(true);
    try {
      const [r, t] = await Promise.all([listResumes(), listResumeTemplates()]);
      setResumes(r);
      setTemplates(t);
      setTemplateId((prev) => {
        if (t.length === 0) return prev;
        if (t.some((x) => x.id === prev)) return prev;
        return t[0].id;
      });
    } catch {
      setOutputNotice("Could not load resumes or templates.");
    } finally {
      setListsLoading(false);
    }
  }, [apiReady]);

  const loadJds = useCallback(async () => {
    if (!apiReady) return;
    try {
      const rows = await listJobDescriptions({ limit: 50 });
      setJds(rows);
    } catch {
      setJds([]);
    }
  }, [apiReady]);

  const recentResumes = useMemo(() => {
    return [...resumes]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 6);
  }, [resumes]);

  useEffect(() => {
    void loadLists();
  }, [loadLists]);

  useEffect(() => {
    setOutputNotice(null);
  }, [sessionId]);

  useEffect(() => {
    if (!apiReady) {
      setJds([]);
      return;
    }
    void loadJds();
  }, [apiReady, loadJds]);

  useEffect(() => {
    if (!sessionId || !apiReady) {
      setSession(null);
      setResumeValue(NONE);
      setJdValue(JD_NONE);
      return;
    }
    let cancelled = false;
    setSessionLoading(true);
    getSession(sessionId)
      .then((s) => {
        if (cancelled) return;
        setSession(s);
        setResumeValue(s.resume_id ?? NONE);
        setJdValue(s.job_description_id ?? JD_NONE);
        if (s.resume_template_id) {
          setTemplateId(s.resume_template_id);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setSession(null);
      })
      .finally(() => {
        if (!cancelled) setSessionLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, apiReady]);

  async function onResumeChange(value: string) {
    if (!sessionId || !apiReady) return;
    setResumeValue(value);
    const id = value === NONE ? null : value;
    try {
      const s = await patchSession(sessionId, { resume_id: id });
      setSession(s);
    } catch {
      setOutputNotice("Failed to update session resume.");
    }
  }

  async function onJdChange(value: string) {
    if (!sessionId || !apiReady) return;
    setJdValue(value);
    const id = value === JD_NONE ? null : value;
    try {
      const s = await patchSession(sessionId, { job_description_id: id });
      setSession(s);
    } catch {
      setOutputNotice("Failed to update active job description.");
    }
  }

  async function onTemplateChange(value: string) {
    if (!sessionId || !apiReady) return;
    setTemplateId(value);
    try {
      const s = await patchSession(sessionId, { resume_template_id: value });
      setSession(s);
    } catch {
      setOutputNotice("Failed to update session template.");
    }
  }

  async function handleUploadResume() {
    const f = resumeFileRef.current?.files?.[0];
    if (!apiReady || !f) {
      setOutputNotice("Choose a PDF, TXT, or DOCX file.");
      return;
    }
    setResumeUploadBusy(true);
    setOutputNotice(null);
    try {
      await uploadResume(f);
      setAddOpen(false);
      setResumePickLabel(null);
      if (resumeFileRef.current) resumeFileRef.current.value = "";
      await loadLists();
    } catch (e) {
      setOutputNotice(e instanceof Error ? e.message : "Could not upload resume.");
    } finally {
      setResumeUploadBusy(false);
    }
  }

  async function handleDownloadResume(r: ResumeListItem) {
    if (!r.has_file || !apiReady) return;
    setResumeDownloadBusy(r.id);
    setOutputNotice(null);
    try {
      await downloadResumeFile(r.id, r.original_filename || "resume");
    } catch (e) {
      setOutputNotice(e instanceof Error ? e.message : "Could not download resume.");
    } finally {
      setResumeDownloadBusy(null);
    }
  }

  async function handleConfirmDeleteResume() {
    if (!pendingDeleteResumeId || !apiReady) return;
    const id = pendingDeleteResumeId;
    setIsDeletingResume(true);
    setDeleteResumeError(null);
    try {
      await deleteResume(id);
      setPendingDeleteResumeId(null);
      await loadLists();
      if (resumeValue === id) {
        await onResumeChange(NONE);
      }
    } catch (e) {
      setDeleteResumeError(e instanceof Error ? e.message : "Could not delete resume.");
    } finally {
      setIsDeletingResume(false);
    }
  }

  async function handlePasteJd() {
    if (!apiReady || !sessionId) return;
    const text = jdDraft.trim();
    if (!text) return;
    setJdPasteError(null);
    setJdPasteBusy(true);
    try {
      const jd = await createJobDescription({ session_id: sessionId, raw_text: text, set_active: true });
      setJdOpen(false);
      setJdDraft("");
      setJdPasteError(null);
      setJdValue(jd.id);
      const s = await getSession(sessionId);
      setSession(s);
      await loadJds();
    } catch (e) {
      setJdPasteError(e instanceof Error ? e.message : "Could not save job description.");
    } finally {
      setJdPasteBusy(false);
    }
  }

  async function handleGeneratePdf() {
    if (!sessionId || !apiReady || !templateId) return;
    setOutputBusy(true);
    setOutputNotice(null);
    setLastOutput(null);
    try {
      const initial = await createResumeOutput(sessionId, {
        template_id: templateId,
        source_resume_id: resumeValue === NONE ? null : resumeValue,
        job_description_id: session?.job_description_id ?? null,
      });
      let cur = initial;
      const deadline = Date.now() + 180_000;
      while (
        cur.status !== "succeeded" &&
        cur.status !== "failed" &&
        Date.now() < deadline
      ) {
        await sleep(1000);
        cur = await getResumeOutput(cur.id);
      }
      setLastOutput(cur);
      if (cur.status === "failed") {
        setOutputNotice(cur.error_text || "PDF job failed.");
      } else if (cur.status !== "succeeded") {
        setOutputNotice("Timed out waiting for PDF — is the worker running and the API able to compile LaTeX?");
      }
    } catch (e) {
      setOutputNotice(e instanceof Error ? e.message : "PDF job error.");
    } finally {
      setOutputBusy(false);
    }
  }

  if (!sessionId) {
    return (
      <ContextPanelOuter
        variant={variant}
        className={cn(
          variant === "embedded"
            ? "flex min-h-0 w-full flex-1 flex-col"
            : "hidden w-[320px] shrink-0 lg:block xl:w-[360px]",
        )}
      >
        <Card className="h-full border border-border/40 bg-card/80 shadow-sm ring-0 backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-1 border-b border-border/35 bg-muted/5 pb-4">
            <CardTitle className="text-base font-semibold tracking-tight">Workspace</CardTitle>
            <CardDescription className="text-sm leading-relaxed">
              Open or start a chat — then link a resume, job description, template, and PDF output here.
            </CardDescription>
          </CardHeader>
        </Card>
      </ContextPanelOuter>
    );
  }

  return (
    <ContextPanelOuter
      variant={variant}
      className={cn(
        variant === "embedded"
          ? "flex min-h-0 w-full flex-col"
          : "hidden w-[320px] shrink-0 lg:block xl:w-[400px]",
      )}
    >
      <div
        className={cn(
          "flex min-h-0 flex-col gap-3",
          variant === "embedded" ? "" : "h-full overflow-hidden",
        )}
      >
        <div className="shrink-0 px-2">
          {sessionLoading ? (
            <Skeleton className="h-4 w-full max-w-[280px] rounded-md" />
          ) : session ? (
            <p
              className="truncate font-mono text-[11px] text-muted-foreground"
              title={session.id}
            >
              Session {session.id}
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">Could not load session.</p>
          )}
        </div>

        <div
          className={cn(
            "flex flex-col gap-3 text-sm leading-relaxed",
            variant === "embedded"
              ? "px-2 pb-4 pt-3"
              : "min-h-0 flex-1 overflow-y-auto px-1 pb-3 pr-2 pt-2",
          )}
        >
          {outputNotice ? (
            <Alert variant="destructive">
              <AlertTitle>Something went wrong</AlertTitle>
              <AlertDescription>{outputNotice}</AlertDescription>
            </Alert>
          ) : null}

          <Card className="shrink-0 border border-border/40 bg-card/80 shadow-sm ring-0 backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/35 bg-muted/5 pb-3">
              <div className="flex flex-row flex-wrap items-start justify-between gap-2">
                <CardTitle className="text-base font-semibold tracking-tight">Resume</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!apiReady}
                  type="button"
                  onClick={() => setAddOpen(true)}
                >
                  Upload resume
                </Button>
              </div>
              <CardDescription className="text-xs leading-relaxed">
                Choose which resume this chat uses for tailoring and PDFs.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 p-4">
              {listsLoading ? (
                <Skeleton className="h-8 w-full" />
              ) : (
                <Select value={resumeValue} onValueChange={(v) => void onResumeChange(v ?? NONE)}>
                  <SelectTrigger className="w-full" size="sm">
                    <SelectValue placeholder="Choose a resume…">
                      {(value) => labelResumeSelectValue(value, resumes, NONE)}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>No resume selected</SelectItem>
                    {resumes.map((r) => (
                      <SelectItem key={r.id} value={r.id}>
                        {r.original_filename?.trim() || `${r.id.slice(0, 8)}…`} (
                        {new Date(r.created_at).toLocaleDateString()})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              {recentResumes.length > 0 ? (
                <div className="flex flex-col gap-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Recent
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {recentResumes.map((r) => {
                      const isSelected = resumeValue === r.id;
                      return (
                        <div
                          key={r.id}
                          data-state={isSelected ? "selected" : undefined}
                          className={cn(
                            "flex flex-row items-center gap-1 pr-1",
                            listRowClasses(isSelected),
                          )}
                        >
                          <button
                            type="button"
                            aria-current={isSelected ? "true" : undefined}
                            onClick={() => void onResumeChange(r.id)}
                            className="flex min-w-0 flex-1 flex-row items-center justify-between gap-2 px-2.5 py-2 text-left text-xs hover:bg-muted/20"
                          >
                            <span className="min-w-0 truncate font-mono text-[11px]">{r.id.slice(0, 8)}…</span>
                            {r.parse_pending ? (
                              <Badge variant="outline" className="shrink-0 text-[10px]">
                                Parsing…
                              </Badge>
                            ) : !r.has_file ? (
                              <Badge variant="destructive" className="shrink-0 text-[10px]">
                                No file
                              </Badge>
                            ) : null}
                          </button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon-sm"
                            disabled={!apiReady || !r.has_file || resumeDownloadBusy === r.id}
                            className="shrink-0 text-muted-foreground hover:text-foreground"
                            aria-label={`Download resume ${r.id.slice(0, 8)}`}
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              void handleDownloadResume(r);
                            }}
                          >
                            <Download className="size-3.5" strokeWidth={2} />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon-sm"
                            disabled={!apiReady || r.parsed_json == null}
                            className="shrink-0 text-muted-foreground hover:text-foreground"
                            aria-label={`View parsed JSON ${r.id.slice(0, 8)}`}
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setResumeJsonView(r);
                            }}
                          >
                            <Braces className="size-3.5" strokeWidth={2} />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon-sm"
                            disabled={!apiReady || isDeletingResume}
                            className="shrink-0 text-muted-foreground hover:text-destructive"
                            aria-label={`Delete resume ${r.id.slice(0, 8)}`}
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              setDeleteResumeError(null);
                              setPendingDeleteResumeId(r.id);
                            }}
                          >
                            <Trash2 className="size-3.5" strokeWidth={2} />
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="shrink-0 border border-border/40 bg-card/80 shadow-sm ring-0 backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/35 bg-muted/5 pb-3">
              <div className="flex flex-row flex-wrap items-start justify-between gap-2">
                <CardTitle className="text-base font-semibold tracking-tight">Job description</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!apiReady}
                  type="button"
                  onClick={() => setJdOpen(true)}
                >
                  Paste posting
                </Button>
              </div>
              <CardDescription className="text-xs leading-relaxed">
                Choose which saved posting is active for this chat (or None). Paste posting saves to the shared
                library and sets it active here.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 p-4">
              <Select value={jdValue} onValueChange={(v) => void onJdChange(v ?? JD_NONE)}>
                <SelectTrigger className="w-full" size="sm">
                  <SelectValue placeholder="Choose a job description…">
                    {(value) => labelJobSelectValue(value, jds, JD_NONE)}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={JD_NONE}>No job description selected</SelectItem>
                  {jds.map((jd) => (
                    <SelectItem key={jd.id} value={jd.id}>
                      {jd.id.slice(0, 8)}… ({new Date(jd.created_at).toLocaleDateString()})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card className="shrink-0 border border-border/40 bg-card/80 shadow-sm ring-0 backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/35 bg-muted/5 pb-3">
              <div className="flex flex-row flex-wrap items-start justify-between gap-2">
                <CardTitle className="text-base font-semibold tracking-tight">Template</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!apiReady}
                  type="button"
                  onClick={() => setTemplateManagerOpen(true)}
                >
                  Manage
                </Button>
              </div>
              <CardDescription className="text-xs leading-relaxed">
                Layout used when you export a PDF.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 p-4">
              {listsLoading ? (
                <Skeleton className="h-8 w-full" />
              ) : templates.length === 0 ? (
                <div className="text-xs text-muted-foreground">No templates available.</div>
              ) : (
                <Select value={templateId} onValueChange={(v) => v && void onTemplateChange(v)}>
                  <SelectTrigger className="w-full" size="sm">
                    <SelectValue placeholder="Choose a template…">
                      {(value) => labelTemplateSelectValue(value, templates)}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </CardContent>
          </Card>

          <Card className="shrink-0 border border-border/40 bg-card/80 shadow-sm ring-0 backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/35 bg-muted/5 pb-3">
              <CardTitle className="text-base font-semibold tracking-tight">Resume output</CardTitle>
              <CardDescription className="text-xs leading-relaxed">
                Build a PDF using this chat&apos;s resume, job, and template.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 p-4">
              <Button
                className="font-medium shadow-sm"
                disabled={!apiReady || outputBusy || !templateId || templates.length === 0}
                onClick={() => void handleGeneratePdf()}
              >
                {outputBusy ? "Working…" : "Generate PDF"}
              </Button>
              {lastOutput ? (
                <div className="flex flex-col gap-2 rounded-xl border border-border/80 bg-muted/15 p-3">
                  <div className="flex flex-row flex-wrap items-center gap-2">
                    <Badge variant={lastOutput.status === "succeeded" ? "default" : "secondary"}>
                      {lastOutput.status}
                    </Badge>
                    <span className="break-all font-mono text-[11px] text-muted-foreground">
                      {lastOutput.id}
                    </span>
                  </div>
                  {lastOutput.status === "succeeded" ? (
                    <a
                      className="text-xs text-primary underline underline-offset-4"
                      href={resumeOutputPdfUrl(lastOutput.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open PDF
                    </a>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>

      <TemplateManagerSheet
        open={templateManagerOpen}
        onOpenChange={setTemplateManagerOpen}
        onTemplatesChanged={() => void loadLists()}
      />

      <Dialog open={resumeJsonView != null} onOpenChange={(open) => !open && setResumeJsonView(null)}>
        <DialogContent className="flex max-h-[85vh] max-w-2xl flex-col gap-0 p-0 sm:max-w-2xl">
          <DialogHeader className="shrink-0 border-b border-border/70 px-6 py-4 text-left">
            <DialogTitle>Parsed resume data</DialogTitle>
            <DialogDescription className="font-mono text-xs">
              {resumeJsonView?.original_filename ?? "Resume"} · {resumeJsonView?.id.slice(0, 8)}…
            </DialogDescription>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-auto px-6 py-3">
            <pre className="whitespace-pre-wrap wrap-break-word rounded-lg border border-border/80 bg-muted/30 p-3 font-mono text-[11px] leading-relaxed text-foreground">
              {resumeJsonView?.parsed_json != null
                ? JSON.stringify(resumeJsonView.parsed_json, null, 2)
                : ""}
            </pre>
          </div>
          <DialogFooter className="shrink-0 border-t border-border/70 px-6 py-3 sm:justify-end">
            <Button type="button" variant="outline" onClick={() => setResumeJsonView(null)}>
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
            setResumePickLabel(null);
            if (resumeFileRef.current) resumeFileRef.current.value = "";
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload resume</DialogTitle>
            <DialogDescription>
              PDF, TXT, or DOCX. After upload you can link it to this chat from the list.
            </DialogDescription>
          </DialogHeader>
          <input
            ref={resumeFileRef}
            type="file"
            accept=".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              setResumePickLabel(file ? file.name : null);
            }}
          />
          <div className="flex flex-col gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!apiReady || resumeUploadBusy}
              onClick={() => resumeFileRef.current?.click()}
            >
              {resumePickLabel ? "Change file" : "Choose file"}
            </Button>
            {resumePickLabel ? (
              <p className="text-xs text-muted-foreground">
                Selected: <span className="text-foreground">{resumePickLabel}</span>
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">No file selected.</p>
            )}
          </div>
          <DialogFooter className="flex flex-row gap-2 sm:justify-end">
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={resumeUploadBusy}>
              Cancel
            </Button>
            <Button
              disabled={!apiReady || resumeUploadBusy || !resumePickLabel}
              onClick={() => void handleUploadResume()}
            >
              {resumeUploadBusy ? "Uploading…" : "Upload"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={pendingDeleteResumeId != null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDeleteResumeId(null);
            setDeleteResumeError(null);
          }
        }}
      >
        <DialogContent showCloseButton className="gap-0 sm:max-w-md">
          <DialogHeader className="flex flex-col gap-2 pr-8 text-left">
            <DialogTitle className="leading-snug">Delete this resume?</DialogTitle>
            <DialogDescription>
              This removes the resume. If this chat was using it, the selection will clear. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteResumeError ? (
            <p className="mt-3 text-sm leading-relaxed text-destructive">{deleteResumeError}</p>
          ) : null}
          <div className="mt-4 flex flex-col-reverse gap-2 border-t border-border/70 pt-3 sm:flex-row sm:justify-end sm:gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={isDeletingResume}
              className="w-full sm:w-auto"
              onClick={() => {
                setPendingDeleteResumeId(null);
                setDeleteResumeError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={isDeletingResume}
              className="w-full font-medium sm:w-auto"
              onClick={() => void handleConfirmDeleteResume()}
            >
              {isDeletingResume ? "Deleting…" : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <PasteJobDescriptionDialog
        open={jdOpen}
        onOpenChange={(o) => {
          setJdOpen(o);
          if (!o) {
            setJdDraft("");
            setJdPasteError(null);
          }
        }}
        title="Paste job posting"
        description={
          <>
            Saves the text to the shared library and sets it as the active posting for your selected chat (for PDFs
            and tailoring).
          </>
        }
        value={jdDraft}
        onValueChange={setJdDraft}
        error={jdPasteError}
        confirmLabel="Save and set active"
        confirmBusyLabel="Saving…"
        onConfirm={handlePasteJd}
        isSubmitting={jdPasteBusy}
        confirmDisabled={!apiReady || !sessionId}
      />
    </ContextPanelOuter>
  );
}
