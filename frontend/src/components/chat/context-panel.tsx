"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createResume,
  createResumeOutput,
  getResumeOutput,
  getSession,
  listResumes,
  listResumeTemplates,
  patchSession,
  resumeOutputPdfUrl,
  type ResumeListItem,
  type ResumeOutputResponse,
  type ResumeTemplateListItem,
  type SessionResponse,
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

const NONE = "__none__";

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
  const [templateId, setTemplateId] = useState<string>("ats-v1");
  const [resumeValue, setResumeValue] = useState<string>(NONE);
  const [listsLoading, setListsLoading] = useState(true);
  const [lastOutput, setLastOutput] = useState<ResumeOutputResponse | null>(null);
  const [outputBusy, setOutputBusy] = useState(false);
  const [outputNotice, setOutputNotice] = useState<string | null>(null);

  const [addOpen, setAddOpen] = useState(false);
  const [newFilename, setNewFilename] = useState("resume.pdf");

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
      return;
    }
    let cancelled = false;
    setSessionLoading(true);
    getSession(sessionId)
      .then((s) => {
        if (cancelled) return;
        setSession(s);
        setResumeValue(s.selected_resume_id ?? NONE);
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
      const s = await patchSession(sessionId, { selected_resume_id: id });
      setSession(s);
    } catch {
      setOutputNotice("Failed to update session resume.");
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
      setOutputNotice("Could not create resume stub.");
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
        job_description_id: null,
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
          <CardHeader className="space-y-1 border-b border-border/60 bg-muted/15 pb-4">
            <CardTitle className="text-base font-semibold tracking-tight">Workspace</CardTitle>
            <CardDescription className="text-sm leading-relaxed">
              Select or create a chat to manage resumes and PDFs.
            </CardDescription>
          </CardHeader>
        </Card>
      </aside>
    );
  }

  return (
    <aside className="hidden w-[360px] shrink-0 md:block">
      <Card className="flex h-full flex-col overflow-hidden border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
        <CardHeader className="space-y-1 border-b border-border/60 bg-muted/15 pb-4">
          <CardTitle className="text-base font-semibold tracking-tight">Workspace</CardTitle>
          <CardDescription className="text-sm leading-relaxed">
            Session tools and resume PDF pipeline.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto text-sm leading-relaxed">
          {outputNotice ? (
            <Alert variant="destructive">
              <AlertTitle>Something went wrong</AlertTitle>
              <AlertDescription>{outputNotice}</AlertDescription>
            </Alert>
          ) : null}

          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Session
            </div>
            {sessionLoading ? (
              <Skeleton className="h-16 w-full rounded-xl" />
            ) : session ? (
              <div className="flex flex-col gap-1.5 rounded-xl border border-border/80 bg-muted/20 p-3 text-xs text-muted-foreground">
                <div className="break-all font-mono text-[11px] leading-snug text-foreground">
                  {session.id}
                </div>
                <div>Resume: {session.selected_resume_id ?? "—"}</div>
                <div>JD id: {session.active_jd_id ?? "—"}</div>
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">Could not load session.</div>
            )}
          </div>

          <Separator />

          <div className="flex flex-col gap-2">
            <div className="flex flex-row items-center justify-between gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Resumes
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled={!apiReady}
                type="button"
                onClick={() => setAddOpen(true)}
              >
                Add stub
              </Button>
            </div>
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
          </div>

          <Separator />

          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Template
            </div>
            {listsLoading ? (
              <Skeleton className="h-8 w-full" />
            ) : templates.length === 0 ? (
              <div className="text-xs text-muted-foreground">No templates from API.</div>
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
          </div>

          <Separator />

          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              PDF output
            </div>
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
          </div>

          <Separator />

          <Alert>
            <AlertTitle>Job descriptions</AlertTitle>
            <AlertDescription>
              There is no REST API yet to create or list job descriptions. When it exists, you can
              attach a JD id to PDF generation and session state.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create resume record</DialogTitle>
            <DialogDescription>
              Stores metadata only (Phase 1). Enter a display filename.
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
    </aside>
  );
}
