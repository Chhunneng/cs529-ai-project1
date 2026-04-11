"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createStandaloneResumeOutput,
  deleteResumeOutput,
  deleteSessionPdfArtifact,
  getResumeOutput,
  listJobDescriptions,
  listPdfArtifacts,
  listResumes,
  listResumeOutputs,
  listResumeTemplates,
  resumeOutputPdfUrl,
  sessionPdfArtifactFileUrl,
  type JobDescriptionResponse,
  type PdfArtifactListItem,
  type ResumeListItem,
  type ResumeOutputResponse,
  type ResumeTemplateListItem,
} from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { SearchableResourceCombobox } from "@/components/ui/searchable-resource-combobox";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateOnlyUtc, formatDateTimeUtc } from "@/lib/format-date";
import { SELECT_NONE as NONE } from "@/lib/select-display";
import { cn } from "@/lib/utils";

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

const PICK = 150;
const LIST_LIMIT = 100;

function shortId(id: string) {
  return `${id.slice(0, 8)}…`;
}

function jobDescriptionPickerLabel(job: JobDescriptionResponse): string {
  const line = job.raw_text.trim().split("\n")[0]?.trim();
  if (line && line.length > 0) {
    return line.length > 72 ? `${line.slice(0, 72)}…` : line;
  }
  return shortId(job.id);
}

export function OutputsPage() {
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [resumesTotal, setResumesTotal] = useState(0);
  const [jobDescriptions, setJobDescriptions] = useState<JobDescriptionResponse[]>([]);
  const [jobDescriptionsTotal, setJobDescriptionsTotal] = useState(0);
  const [templates, setTemplates] = useState<ResumeTemplateListItem[]>([]);
  const [templatesTotal, setTemplatesTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  const [resumeId, setResumeId] = useState<string>(NONE);
  const [jobDescriptionId, setJobDescriptionId] = useState<string>(NONE);
  const [templateId, setTemplateId] = useState<string>(NONE);

  const [busy, setBusy] = useState(false);
  const [lastOutput, setLastOutput] = useState<ResumeOutputResponse | null>(null);

  const [exportOutputs, setExportOutputs] = useState<ResumeOutputResponse[]>([]);
  const [exportTotal, setExportTotal] = useState(0);
  const [chatArtifacts, setChatArtifacts] = useState<PdfArtifactListItem[]>([]);
  const [chatArtifactsTotal, setChatArtifactsTotal] = useState(0);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTitle, setPreviewTitle] = useState("");
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);

  const openPreview = useCallback((title: string, src: string) => {
    setPreviewTitle(title);
    setPreviewSrc(src);
    setPreviewOpen(true);
  }, []);

  const [deletingKey, setDeletingKey] = useState<string | null>(null);

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

  const loadJobDescriptionsPicker = useCallback(async () => {
    try {
      const j = await listJobDescriptions({ limit: PICK, offset: 0 });
      setJobDescriptions(j.items);
      setJobDescriptionsTotal(j.total);
    } catch {
      /* keep */
    }
  }, []);

  const refreshPdfLists = useCallback(async () => {
    try {
      const [outs, arts] = await Promise.all([
        listResumeOutputs({ limit: LIST_LIMIT, offset: 0 }),
        listPdfArtifacts({ limit: LIST_LIMIT, offset: 0 }),
      ]);
      setExportOutputs(outs.items);
      setExportTotal(outs.total);
      setChatArtifacts(arts.items);
      setChatArtifactsTotal(arts.total);
    } catch {
      /* keep existing rows */
    }
  }, []);

  const handleDeleteExport = useCallback(
    async (row: ResumeOutputResponse) => {
      if (row.status === "queued" || row.status === "running") return;
      if (!window.confirm("Delete this export and its files from the server? This cannot be undone.")) return;
      const key = `out:${row.id}`;
      setDeletingKey(key);
      setNotice(null);
      try {
        await deleteResumeOutput(row.id);
        setLastOutput((cur) => (cur?.id === row.id ? null : cur));
        const inline = resumeOutputPdfUrl(row.id, { disposition: "inline" });
        setPreviewSrc((cur) => {
          if (cur === inline) {
            setPreviewOpen(false);
            setPreviewTitle("");
            return null;
          }
          return cur;
        });
        await refreshPdfLists();
      } catch (e) {
        setNotice(e instanceof Error ? e.message : "Delete failed.");
      } finally {
        setDeletingKey(null);
      }
    },
    [refreshPdfLists],
  );

  const handleDeleteChatArtifact = useCallback(
    async (row: PdfArtifactListItem) => {
      if (
        !window.confirm(
          "Delete this chat PDF from the server? Messages that pointed to it will lose the attachment. This cannot be undone.",
        )
      ) {
        return;
      }
      const key = `art:${row.id}`;
      setDeletingKey(key);
      setNotice(null);
      try {
        await deleteSessionPdfArtifact(row.session_id, row.id);
        const inline = sessionPdfArtifactFileUrl(row.session_id, row.id, { disposition: "inline" });
        setPreviewSrc((cur) => {
          if (cur === inline) {
            setPreviewOpen(false);
            setPreviewTitle("");
            return null;
          }
          return cur;
        });
        await refreshPdfLists();
      } catch (e) {
        setNotice(e instanceof Error ? e.message : "Delete failed.");
      } finally {
        setDeletingKey(null);
      }
    },
    [refreshPdfLists],
  );

  const loadAll = useCallback(async () => {
    setNotice(null);
    setLoading(true);
    try {
      const [r, j, t, outs, arts] = await Promise.all([
        listResumes({ limit: PICK, offset: 0 }),
        listJobDescriptions({ limit: PICK, offset: 0 }),
        listResumeTemplates({ limit: PICK, offset: 0 }),
        listResumeOutputs({ limit: LIST_LIMIT, offset: 0 }),
        listPdfArtifacts({ limit: LIST_LIMIT, offset: 0 }),
      ]);
      setResumes(r.items);
      setResumesTotal(r.total);
      setJobDescriptions(j.items);
      setJobDescriptionsTotal(j.total);
      setTemplates(t.items);
      setTemplatesTotal(t.total);
      setExportOutputs(outs.items);
      setExportTotal(outs.total);
      setChatArtifacts(arts.items);
      setChatArtifactsTotal(arts.total);
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

  const jobDescriptionOptions = useMemo(
    () =>
      jobDescriptions.map((jd) => ({
        value: jd.id,
        label: jobDescriptionPickerLabel(jd),
        description: formatDateOnlyUtc(jd.created_at),
      })),
    [jobDescriptions],
  );

  const resumeOptions = useMemo(
    () =>
      resumes.map((r) => ({
        value: r.id,
        label: r.original_filename?.trim() || `${r.id.slice(0, 8)}…`,
        description: formatDateOnlyUtc(r.created_at),
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
    return (
      !busy &&
      templateId !== NONE &&
      resumeId !== NONE &&
      jobDescriptionId !== NONE
    );
  }, [busy, templateId, resumeId, jobDescriptionId]);

  async function handleGenerate() {
    if (!canGenerate) return;
    setBusy(true);
    setNotice(null);
    setLastOutput(null);
    try {
      const initial = await createStandaloneResumeOutput({
        template_id: templateId,
        source_resume_id: resumeId,
        job_description_id: jobDescriptionId,
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
      await refreshPdfLists();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Generate error.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Dialog
        open={previewOpen}
        onOpenChange={(open) => {
          setPreviewOpen(open);
          if (!open) {
            setPreviewSrc(null);
            setPreviewTitle("");
          }
        }}
      >
        <DialogContent showCloseButton className="max-h-[90vh] gap-0 p-0 sm:max-w-4xl">
          <DialogHeader className="border-b border-border/60 px-4 py-3 pr-10 text-left">
            <DialogTitle className="text-sm font-semibold">{previewTitle || "PDF preview"}</DialogTitle>
            <DialogDescription className="text-xs">
              Close this window when you are done reading. Use Download if you want a file on your computer.
            </DialogDescription>
          </DialogHeader>
          {previewSrc ? (
            <iframe title="PDF preview" className="h-[min(80vh,720px)] w-full rounded-b-xl bg-muted/30" src={previewSrc} />
          ) : null}
        </DialogContent>
      </Dialog>

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
              PDF layout comes from the LaTeX template you pick. The app fills the template using your resume text and
              the job description you select (tailored for ATS-friendly wording).
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
                      Resume
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
                      Job description
                    </div>
                    <SearchableResourceCombobox
                      value={jobDescriptionId}
                      onValueChange={(v) => setJobDescriptionId(v)}
                      options={jobDescriptionOptions}
                      noneValue={NONE}
                      noneLabel="No job description selected"
                      placeholder="Choose a job description…"
                      searchPlaceholder="Reload list…"
                      onQueryChange={() => void loadJobDescriptionsPicker()}
                      totalHint={
                        jobDescriptionsTotal > jobDescriptions.length
                          ? `Showing ${jobDescriptions.length} of ${jobDescriptionsTotal}`
                          : jobDescriptionsTotal > 0
                            ? `${jobDescriptionsTotal} saved`
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
                      <div className="flex flex-row flex-wrap gap-3 text-xs">
                        <button
                          type="button"
                          className="text-primary underline underline-offset-4"
                          onClick={() =>
                            openPreview(
                              `Export ${shortId(lastOutput.id)}`,
                              resumeOutputPdfUrl(lastOutput.id, { disposition: "inline" }),
                            )
                          }
                        >
                          Preview PDF
                        </button>
                        <a
                          className="text-primary underline underline-offset-4"
                          href={resumeOutputPdfUrl(lastOutput.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Download PDF
                        </a>
                      </div>
                    ) : lastOutput.status === "failed" && lastOutput.error_text ? (
                      <p className="text-xs leading-relaxed text-destructive">{lastOutput.error_text}</p>
                    ) : null}
                  </div>
                ) : null}
              </>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15">
            <CardTitle className="text-base font-semibold tracking-tight">PDF exports (from this page)</CardTitle>
            <CardDescription className="max-w-prose text-sm leading-relaxed">
              Each export is stored as its own row. Preview opens inside the app; Download opens the file in a new tab
              so your browser can save it.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-4">
                <Skeleton className="h-24 w-full" />
              </div>
            ) : exportOutputs.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">No exports yet. Generate one above.</p>
            ) : (
              <div className="flex flex-col">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-border/70 bg-muted/20 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        <th className="px-3 py-2 font-medium whitespace-nowrap">Created</th>
                        <th className="px-3 py-2 font-medium whitespace-nowrap">Chat session</th>
                        <th className="px-3 py-2 font-medium whitespace-nowrap">Status</th>
                        <th className="px-3 py-2 text-right font-medium whitespace-nowrap">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exportOutputs.map((row) => {
                        const ready = row.status === "succeeded" && Boolean(row.pdf_path);
                        const blockDelete = row.status === "queued" || row.status === "running";
                        const rowDeleting = deletingKey === `out:${row.id}`;
                        return (
                          <tr key={row.id} className="border-b border-border/60 last:border-0">
                            <td className="px-3 py-3 align-middle text-muted-foreground whitespace-nowrap">
                              {formatDateTimeUtc(row.created_at)}
                            </td>
                            <td className="px-3 py-3 align-middle font-mono text-xs text-muted-foreground">
                              {row.session_id ? shortId(row.session_id) : "—"}
                            </td>
                            <td className="px-3 py-3 align-middle">
                              <Badge variant={row.status === "succeeded" ? "default" : "secondary"} className="w-fit">
                                {row.status}
                              </Badge>
                            </td>
                            <td className="px-3 py-3 align-middle text-right">
                              <div className="inline-flex flex-row flex-wrap justify-end gap-2">
                                <Button
                                  type="button"
                                  variant="secondary"
                                  size="sm"
                                  disabled={!ready || rowDeleting || Boolean(deletingKey)}
                                  onClick={() =>
                                    openPreview(
                                      `Export ${shortId(row.id)}`,
                                      resumeOutputPdfUrl(row.id, { disposition: "inline" }),
                                    )
                                  }
                                >
                                  Preview
                                </Button>
                                {ready ? (
                                  <a
                                    className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                                    href={resumeOutputPdfUrl(row.id)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    Download
                                  </a>
                                ) : (
                                  <span
                                    className={cn(
                                      buttonVariants({ variant: "outline", size: "sm" }),
                                      "pointer-events-none opacity-50",
                                    )}
                                  >
                                    Download
                                  </span>
                                )}
                                <Button
                                  type="button"
                                  variant="destructive"
                                  size="sm"
                                  disabled={blockDelete || rowDeleting || Boolean(deletingKey)}
                                  onClick={() => void handleDeleteExport(row)}
                                >
                                  {rowDeleting ? "…" : "Delete"}
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {exportTotal > exportOutputs.length ? (
                  <p className="border-t border-border/70 px-3 py-2 text-xs text-muted-foreground">
                    Showing {exportOutputs.length} of {exportTotal} exports.
                  </p>
                ) : null}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15">
            <CardTitle className="text-base font-semibold tracking-tight">PDFs from chat</CardTitle>
            <CardDescription className="max-w-prose text-sm leading-relaxed">
              These files are created when the assistant finishes a resume-PDF job in Chat. They are not the same rows
              as the export list above, but you can preview or download them the same way.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-4">
                <Skeleton className="h-24 w-full" />
              </div>
            ) : chatArtifacts.length === 0 ? (
              <p className="p-4 text-sm text-muted-foreground">No chat PDFs yet.</p>
            ) : (
              <div className="flex flex-col">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[32rem] border-collapse text-left text-sm">
                    <thead>
                      <tr className="border-b border-border/70 bg-muted/20 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        <th className="px-3 py-2 font-medium whitespace-nowrap">Created</th>
                        <th className="px-3 py-2 font-medium whitespace-nowrap">Session</th>
                        <th className="px-3 py-2 text-right font-medium whitespace-nowrap">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {chatArtifacts.map((row) => {
                        const rowDeleting = deletingKey === `art:${row.id}`;
                        return (
                          <tr key={row.id} className="border-b border-border/60 last:border-0">
                            <td className="px-3 py-3 align-middle text-muted-foreground whitespace-nowrap">
                              {formatDateTimeUtc(row.created_at)}
                            </td>
                            <td className="px-3 py-3 align-middle font-mono text-xs text-muted-foreground">
                              {shortId(row.session_id)}
                            </td>
                            <td className="px-3 py-3 align-middle text-right">
                              <div className="inline-flex flex-row flex-wrap justify-end gap-2">
                                <Button
                                  type="button"
                                  variant="secondary"
                                  size="sm"
                                  disabled={rowDeleting || Boolean(deletingKey)}
                                  onClick={() =>
                                    openPreview(
                                      `Chat PDF ${shortId(row.id)}`,
                                      sessionPdfArtifactFileUrl(row.session_id, row.id, { disposition: "inline" }),
                                    )
                                  }
                                >
                                  Preview
                                </Button>
                                <a
                                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                                  href={sessionPdfArtifactFileUrl(row.session_id, row.id)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  Download
                                </a>
                                <Button
                                  type="button"
                                  variant="destructive"
                                  size="sm"
                                  disabled={rowDeleting || Boolean(deletingKey)}
                                  onClick={() => void handleDeleteChatArtifact(row)}
                                >
                                  {rowDeleting ? "…" : "Delete"}
                                </Button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {chatArtifactsTotal > chatArtifacts.length ? (
                  <p className="border-t border-border/70 px-3 py-2 text-xs text-muted-foreground">
                    Showing {chatArtifacts.length} of {chatArtifactsTotal} chat PDFs.
                  </p>
                ) : null}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
