"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createResumeOutput,
  getResumeOutput,
  getSession,
  listResumes,
  listResumeTemplates,
  listSessions,
  resumeOutputPdfUrl,
  type ResumeListItem,
  type ResumeOutputResponse,
  type ResumeTemplateListItem,
  type SessionResponse,
} from "@/lib/api";
import { AppPageHeader } from "@/components/layout/app-page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { SearchableResourceCombobox } from "@/components/ui/searchable-resource-combobox";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { SELECT_NONE as NONE } from "@/lib/select-display";

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

const PICK = 150;

export function OutputsPage() {
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [resumesTotal, setResumesTotal] = useState(0);
  const [templates, setTemplates] = useState<ResumeTemplateListItem[]>([]);
  const [templatesTotal, setTemplatesTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string>(NONE);
  const [resumeId, setResumeId] = useState<string>(NONE);
  const [templateId, setTemplateId] = useState<string>(NONE);
  const [activeJdId, setActiveJdId] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);
  const [lastOutput, setLastOutput] = useState<ResumeOutputResponse | null>(null);

  const loadResumesPicker = useCallback(async (q: string) => {
    try {
      const r = await listResumes({
        limit: PICK,
        offset: 0,
        ...(q.trim() ? { q: q.trim() } : {}),
      });
      setResumes(r.items);
      setResumesTotal(r.total);
    } catch {
      /* keep */
    }
  }, []);

  const loadTemplatesPicker = useCallback(async (q: string) => {
    try {
      const t = await listResumeTemplates({
        limit: PICK,
        offset: 0,
        ...(q.trim() ? { q: q.trim() } : {}),
      });
      setTemplates(t.items);
      setTemplatesTotal(t.total);
    } catch {
      /* keep */
    }
  }, []);

  const loadAll = useCallback(async () => {
    setNotice(null);
    setLoading(true);
    try {
      const [s, r, t] = await Promise.all([
        listSessions({ limit: PICK, offset: 0 }),
        listResumes({ limit: PICK, offset: 0 }),
        listResumeTemplates({ limit: PICK, offset: 0 }),
      ]);
      setSessions(s.items);
      setSessionsTotal(s.total);
      setResumes(r.items);
      setResumesTotal(r.total);
      setTemplates(t.items);
      setTemplatesTotal(t.total);
      setSessionId((prev) =>
        prev !== NONE ? prev : (s.items[0]?.id ? String(s.items[0].id) : NONE),
      );
      setTemplateId((prev) =>
        prev !== NONE ? prev : (t.items[0]?.id ? String(t.items[0].id) : NONE),
      );
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (sessionId === NONE) {
      setActiveJdId(null);
      return;
    }
    let cancelled = false;
    getSession(sessionId)
      .then((s) => {
        if (!cancelled) setActiveJdId(s.job_description_id);
      })
      .catch(() => {
        if (!cancelled) setActiveJdId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const sessionOptions = useMemo(
    () =>
      sessions.map((s) => ({
        value: String(s.id),
        label: `${String(s.id).slice(0, 8)}…`,
        description: new Date(s.created_at).toLocaleDateString(),
      })),
    [sessions],
  );

  const resumeOptions = useMemo(
    () =>
      resumes.map((r) => ({
        value: r.id,
        label: r.original_filename?.trim() || `${r.id.slice(0, 8)}…`,
        description: new Date(r.created_at).toLocaleDateString(),
      })),
    [resumes],
  );

  const templateOptions = useMemo(
    () =>
      templates.map((t) => ({
        value: String(t.id),
        label: t.name,
        description: t.valid ? "Ready" : "Needs fix",
      })),
    [templates],
  );

  const canGenerate = useMemo(() => {
    return !busy && sessionId !== NONE && templateId !== NONE;
  }, [busy, sessionId, templateId]);

  async function handleGenerate() {
    if (!canGenerate) return;
    setBusy(true);
    setNotice(null);
    setLastOutput(null);
    try {
      const initial = await createResumeOutput(sessionId, {
        template_id: templateId,
        source_resume_id: resumeId === NONE ? null : resumeId,
        job_description_id: activeJdId ?? null,
      });
      let cur = initial;
      const deadline = Date.now() + 180_000;
      while (cur.status !== "succeeded" && cur.status !== "failed" && Date.now() < deadline) {
        await sleep(1000);
        cur = await getResumeOutput(cur.id);
      }
      setLastOutput(cur);
      if (cur.status === "failed") {
        setNotice(cur.error_text || "Output job failed.");
      } else if (cur.status !== "succeeded") {
        setNotice("Timed out waiting for PDF — is the worker running?");
      }
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Generate error.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <AppPageHeader
        title="PDF exports"
        description="Build a resume PDF from a chat session, optional resume, and the job posting you set as active."
      />

      <div className="flex flex-col gap-4 p-4 md:p-5">
        {notice ? (
          <Alert variant="destructive" className="border-destructive/50">
            <AlertTitle>Something went wrong</AlertTitle>
            <AlertDescription>{notice}</AlertDescription>
          </Alert>
        ) : null}

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15">
            <CardTitle className="text-base font-semibold tracking-tight">Generate PDF</CardTitle>
            <CardDescription className="max-w-prose text-sm leading-relaxed">
              PDF layout comes from the LaTeX template you pick—not from chat styling. If the session has an active
              job posting, it is included. You can also start an export from the Chat workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 p-4">
            {loading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <>
                <div className="flex flex-col gap-3 md:grid md:grid-cols-3">
                  <div className="flex flex-col gap-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Session
                    </div>
                    <SearchableResourceCombobox
                      value={sessionId}
                      onValueChange={(v) => setSessionId(v)}
                      options={sessionOptions}
                      noneValue={NONE}
                      noneLabel="No session selected"
                      placeholder="Choose a session…"
                      searchPlaceholder="Filter loaded sessions…"
                      totalHint={
                        sessionsTotal > sessions.length
                          ? `Showing ${sessions.length} of ${sessionsTotal}`
                          : sessionsTotal > 0
                            ? `${sessionsTotal} chats`
                            : null
                      }
                    />
                    <div className="text-xs text-muted-foreground">Active JD: {activeJdId ?? "—"}</div>
                  </div>

                  <div className="flex flex-col gap-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Resume (optional)
                    </div>
                    <SearchableResourceCombobox
                      value={resumeId}
                      onValueChange={(v) => setResumeId(v)}
                      options={resumeOptions}
                      noneValue={NONE}
                      noneLabel="No resume selected"
                      placeholder="Choose a resume…"
                      searchPlaceholder="Search by filename…"
                      onQueryChange={loadResumesPicker}
                      totalHint={
                        resumesTotal > resumes.length
                          ? `Showing ${resumes.length} of ${resumesTotal}`
                          : resumesTotal > 0
                            ? `${resumesTotal} resumes`
                            : null
                      }
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Template
                    </div>
                    <SearchableResourceCombobox
                      value={templateId}
                      onValueChange={(v) => setTemplateId(v)}
                      options={templateOptions}
                      noneValue={NONE}
                      noneLabel="No template selected"
                      placeholder="Choose a template…"
                      searchPlaceholder="Search templates…"
                      onQueryChange={loadTemplatesPicker}
                      totalHint={
                        templatesTotal > templates.length
                          ? `Showing ${templates.length} of ${templatesTotal}`
                          : templatesTotal > 0
                            ? `${templatesTotal} templates`
                            : null
                      }
                    />
                  </div>
                </div>

                <Separator />

                <div className="flex flex-row flex-wrap items-center justify-between gap-3">
                  <Button disabled={!canGenerate} onClick={() => void handleGenerate()}>
                    {busy ? "Working…" : "Generate PDF"}
                  </Button>
                  <Button variant="secondary" disabled={loading} onClick={() => void loadAll()}>
                    Refresh lists
                  </Button>
                </div>

                {lastOutput ? (
                  <div className="flex flex-col gap-2 rounded-xl border border-border/80 bg-muted/10 p-3">
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
                    ) : lastOutput.status === "failed" && lastOutput.error_text ? (
                      <p className="text-xs leading-relaxed text-destructive">{lastOutput.error_text}</p>
                    ) : null}
                  </div>
                ) : null}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
