"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Trash2 } from "lucide-react";

import {
  activateJobDescription,
  createJobDescription,
  createResume,
  createResumeOutput,
  deleteResume,
  getResumeOutput,
  getSession,
  listJobDescriptions,
  listResumes,
  listResumeTemplates,
  patchSession,
  resumeOutputPdfUrl,
  type JobDescriptionResponse,
  type ResumeListItem,
  type ResumeOutputResponse,
  type ResumeTemplateListItem,
  type SessionResponse,
} from "@/lib/api";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const NONE = "__none__";
const JD_NONE = "__jd_none__";

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export function ContextPanel({
  sessionId,
  apiReady,
}: {
  sessionId: string | null;
  apiReady: boolean;
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
  const [newFilename, setNewFilename] = useState("resume.pdf");
  const [jdOpen, setJdOpen] = useState(false);
  const [jdDraft, setJdDraft] = useState("");

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
    if (!apiReady || !sessionId) return;
    try {
      const rows = await listJobDescriptions({ session_id: sessionId, limit: 50 });
      setJds(rows);
    } catch {
      setJds([]);
    }
  }, [apiReady, sessionId]);

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
    if (!sessionId || !apiReady) {
      setSession(null);
      setResumeValue(NONE);
      setJds([]);
      setJdValue(JD_NONE);
      return;
    }
    let cancelled = false;
    setSessionLoading(true);
    getSession(sessionId)
      .then((s) => {
        if (cancelled) return;
        setSession(s);
        setResumeValue(s.selected_resume_id ?? NONE);
        setJdValue(s.active_jd_id ?? JD_NONE);
      })
      .catch(() => {
        if (cancelled) return;
        setSession(null);
      })
      .finally(() => {
        if (!cancelled) setSessionLoading(false);
      });
    void loadJds();
    return () => {
      cancelled = true;
    };
  }, [sessionId, apiReady, loadJds]);

  async function onResumeChange(value: string) {
    if (!sessionId || !apiReady) return;
    setResumeValue(value);
    const id = value === NONE ? null : value;
    try {
      const s = await patchSession(sessionId, { selected_resume_id: id });
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
      const s = await patchSession(sessionId, { active_jd_id: id });
      setSession(s);
    } catch {
      setOutputNotice("Failed to update active job description.");
    }
  }

  async function handleAddResume() {
    if (!apiReady || !newFilename.trim()) return;
    try {
      await createResume(newFilename.trim());
      setAddOpen(false);
      setNewFilename("resume.pdf");
      await loadLists();
    } catch {
      setOutputNotice("Could not create resume.");
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
    try {
      const jd = await createJobDescription({ session_id: sessionId, raw_text: text, set_active: true });
      setJdOpen(false);
      setJdDraft("");
      setJdValue(jd.id);
      const s = await getSession(sessionId);
      setSession(s);
      await loadJds();
    } catch (e) {
      setOutputNotice(e instanceof Error ? e.message : "Could not save job description.");
    }
  }

  async function handleActivateJd(jdId: string) {
    if (!apiReady || !sessionId) return;
    try {
      await activateJobDescription({ session_id: sessionId, job_description_id: jdId });
      setJdValue(jdId);
      const s = await getSession(sessionId);
      setSession(s);
    } catch (e) {
      setOutputNotice(e instanceof Error ? e.message : "Could not activate job description.");
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
        job_description_id: session?.active_jd_id ?? null,
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
      <aside className="hidden w-[360px] shrink-0 md:block">
        <Card className="h-full border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15 pb-4">
            <CardTitle className="text-base font-semibold tracking-tight">Workspace</CardTitle>
            <CardDescription className="text-sm leading-relaxed">
              Open or start a chat — then link a resume, job description, template, and PDF output here.
            </CardDescription>
          </CardHeader>
        </Card>
      </aside>
    );
  }

  return (
    <aside className="hidden w-[380px] shrink-0 md:block lg:w-[400px]">
      <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden">
        <div className="shrink-0 px-0.5">
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

        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1 text-sm leading-relaxed">
          {outputNotice ? (
            <Alert variant="destructive">
              <AlertTitle>Something went wrong</AlertTitle>
              <AlertDescription>{outputNotice}</AlertDescription>
            </Alert>
          ) : null}

          <Card className="shrink-0 border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15 pb-3">
              <div className="flex flex-row flex-wrap items-start justify-between gap-2">
                <CardTitle className="text-base font-semibold tracking-tight">Resume</CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!apiReady}
                  type="button"
                  onClick={() => setAddOpen(true)}
                >
                  New resume
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
                    <SelectValue placeholder="Link a resume" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>None</SelectItem>
                    {resumes.map((r) => (
                      <SelectItem key={r.id} value={r.id}>
                        {r.id.slice(0, 8)}… ({new Date(r.created_at).toLocaleDateString()})
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
                    {recentResumes.map((r) => (
                      <div
                        key={r.id}
                        className="flex flex-row items-center gap-1 rounded-lg border border-border/70 bg-muted/10 pr-1"
                      >
                        <button
                          type="button"
                          onClick={() => void onResumeChange(r.id)}
                          className="flex min-w-0 flex-1 flex-row items-center justify-between gap-2 px-2.5 py-2 text-left text-xs hover:bg-muted/20"
                        >
                          <span className="min-w-0 truncate font-mono text-[11px]">{r.id.slice(0, 8)}…</span>
                          <Badge
                            variant={resumeValue === r.id ? "default" : "secondary"}
                            className="shrink-0 text-[10px]"
                          >
                            {r.openai_file_id ? "File" : "Draft"}
                          </Badge>
                        </button>
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
                    ))}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="shrink-0 border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15 pb-3">
              <CardTitle className="text-base font-semibold tracking-tight">Job description</CardTitle>
              <CardDescription className="text-xs leading-relaxed">
                Paste job text or pick one to use for tailoring and PDF generation.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 p-4">
              <div className="flex flex-row flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Active
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!apiReady}
                  type="button"
                  onClick={() => setJdOpen(true)}
                >
                  Paste job
                </Button>
              </div>
              <Select value={jdValue} onValueChange={(v) => void onJdChange(v ?? JD_NONE)}>
                <SelectTrigger className="w-full" size="sm">
                  <SelectValue placeholder="Select a job description" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={JD_NONE}>None</SelectItem>
                  {jds.map((jd) => (
                    <SelectItem key={jd.id} value={jd.id}>
                      {jd.id.slice(0, 8)}… ({new Date(jd.created_at).toLocaleDateString()})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {jdValue !== JD_NONE ? (
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!apiReady || !sessionId}
                  type="button"
                  onClick={() => void handleActivateJd(jdValue)}
                >
                  Set active
                </Button>
              ) : null}
            </CardContent>
          </Card>

          <Card className="shrink-0 border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15 pb-3">
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
                <Select value={templateId} onValueChange={(v) => v && setTemplateId(v)}>
                  <SelectTrigger className="w-full" size="sm">
                    <SelectValue placeholder="Template" />
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

          <Card className="shrink-0 border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
            <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15 pb-3">
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

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New resume</DialogTitle>
            <DialogDescription>
              Enter a filename for this draft. You can link it to this chat after it is created.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Input
              value={newFilename}
              onChange={(e) => setNewFilename(e.target.value)}
              placeholder="resume.pdf"
            />
          </div>
          <DialogFooter className="flex flex-row gap-2 sm:justify-end">
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void handleAddResume()}>Create</Button>
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
          <DialogHeader className="space-y-2 pr-8 text-left">
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

      <Dialog open={jdOpen} onOpenChange={setJdOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Paste job description</DialogTitle>
            <DialogDescription>
              Paste the full job description text. It will be saved to this session and used for tailoring.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <textarea
              value={jdDraft}
              onChange={(e) => setJdDraft(e.target.value)}
              placeholder="Paste the job description here…"
              className="min-h-[180px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/25"
            />
          </div>
          <DialogFooter className="flex flex-row gap-2 sm:justify-end">
            <Button variant="outline" onClick={() => setJdOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!jdDraft.trim()} onClick={() => void handlePasteJd()}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  );
}
