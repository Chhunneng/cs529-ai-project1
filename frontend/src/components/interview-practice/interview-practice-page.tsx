"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AppPageHeader } from "@/components/layout/app-page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  createInterviewPracticeSession,
  generateInterviewQuestions,
  getInterviewAnswerAttempt,
  listInterviewPracticeSessions,
  listInterviewQuestions,
  listInterviewSessionAnswers,
  listJobDescriptions,
  listResumes,
  pingBackend,
  streamInterviewJobUntilDone,
  postInterviewAnswer,
  postInterviewRefine,
  type InterviewAnswerAttemptResponse,
  type InterviewAnswerHistoryItem,
  type InterviewJobStatusResponse,
  type InterviewPracticeSessionResponse,
  type InterviewQuestionLevel,
  type InterviewQuestionResponse,
  type InterviewQuestionStyle,
  type InterviewSource,
  type JobDescriptionResponse,
  type ResumeListItem,
} from "@/lib/api";
import { formatDateTimeUtc } from "@/lib/format-date";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "interviewPracticeSessionId";

function metaLabel(meta: Record<string, unknown>): string[] {
  const parts: string[] = [];
  const t = meta.type;
  const d = meta.difficulty;
  const f = meta.focus;
  if (typeof t === "string" && t) parts.push(t);
  if (typeof d === "string" && d) parts.push(d);
  if (typeof f === "string" && f) parts.push(f);
  return parts;
}

export function InterviewPracticePage() {
  const [connection, setConnection] = useState<"checking" | "ready" | "offline">("checking");
  const apiReady = connection === "ready";

  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [jds, setJds] = useState<JobDescriptionResponse[]>([]);
  const [loadLibs, setLoadLibs] = useState(false);
  const [libError, setLibError] = useState<string | null>(null);

  const [selResumeId, setSelResumeId] = useState<string>("");
  const [selJdId, setSelJdId] = useState<string>("");
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [practiceSession, setPracticeSession] = useState<{
    id: string;
    resume_id: string | null;
    job_description_id: string | null;
  } | null>(null);

  const [source, setSource] = useState<InterviewSource>("both");
  const [count, setCount] = useState(8);
  const [questionStyle, setQuestionStyle] = useState<InterviewQuestionStyle>("random");
  const [questionLevel, setQuestionLevel] = useState<InterviewQuestionLevel>("random");
  const [focusDetail, setFocusDetail] = useState("");
  const [generateBusy, setGenerateBusy] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generateProgress, setGenerateProgress] = useState<string | null>(null);

  const [questions, setQuestions] = useState<InterviewQuestionResponse[]>([]);
  const [questionsLoading, setQuestionsLoading] = useState(false);

  const [draftByQuestion, setDraftByQuestion] = useState<Record<string, string>>({});
  const [attemptByQuestion, setAttemptByQuestion] = useState<Record<string, string>>({});
  const [feedbackByQuestion, setFeedbackByQuestion] = useState<
    Record<string, InterviewAnswerAttemptResponse | undefined>
  >({});
  const [submitBusy, setSubmitBusy] = useState<Record<string, boolean>>({});
  const [refineBusy, setRefineBusy] = useState<Record<string, boolean>>({});
  const [feedbackSavedNotice, setFeedbackSavedNotice] = useState<Record<string, boolean>>({});

  const [mainTab, setMainTab] = useState<"practice" | "history">("practice");
  const [historySessions, setHistorySessions] = useState<InterviewPracticeSessionResponse[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
  const [historyAnswers, setHistoryAnswers] = useState<InterviewAnswerHistoryItem[]>([]);
  const [answersLoading, setAnswersLoading] = useState(false);
  const [answersError, setAnswersError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    pingBackend().then((ok) => {
      if (!cancelled) setConnection(ok ? "ready" : "offline");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshLibraries = useCallback(async () => {
    if (!apiReady) return;
    setLibError(null);
    setLoadLibs(true);
    try {
      const [r, j] = await Promise.all([
        listResumes({ limit: 200, offset: 0 }),
        listJobDescriptions({ limit: 200, offset: 0 }),
      ]);
      setResumes(r.items);
      setJds(j.items);
    } catch (e) {
      setLibError(e instanceof Error ? e.message : "Could not load resumes or job postings.");
    } finally {
      setLoadLibs(false);
    }
  }, [apiReady]);

  useEffect(() => {
    void refreshLibraries();
  }, [refreshLibraries]);

  const canSourceJd = Boolean(practiceSession?.job_description_id);
  const canSourceResume = Boolean(practiceSession?.resume_id);

  const sourceValid = useMemo(() => {
    if (!practiceSession) return false;
    if (source === "jd") return canSourceJd;
    if (source === "resume") return canSourceResume;
    return canSourceJd && canSourceResume;
  }, [practiceSession, source, canSourceJd, canSourceResume]);

  const needsFocusDetail = useMemo(
    () => questionStyle === "domain" || questionStyle === "language" || questionStyle === "other",
    [questionStyle],
  );
  const focusDetailValid = !needsFocusDetail || focusDetail.trim().length > 0;

  useEffect(() => {
    if (!practiceSession) return;
    if (source === "both" && (!canSourceJd || !canSourceResume)) {
      if (canSourceJd && !canSourceResume) setSource("jd");
      else if (canSourceResume && !canSourceJd) setSource("resume");
    }
  }, [practiceSession, source, canSourceJd, canSourceResume]);

  async function handleCreateSession() {
    if (!apiReady) return;
    setCreateError(null);
    setCreateBusy(true);
    try {
      const body = {
        resume_id: selResumeId.trim() || null,
        job_description_id: selJdId.trim() || null,
      };
      const row = await createInterviewPracticeSession(body);
      setPracticeSession({
        id: row.id,
        resume_id: row.resume_id,
        job_description_id: row.job_description_id,
      });
      setQuestions([]);
      setAttemptByQuestion({});
      setFeedbackByQuestion({});
      setDraftByQuestion({});
      setFeedbackSavedNotice({});
      try {
        localStorage.setItem(STORAGE_KEY, row.id);
      } catch {
        /* ignore */
      }
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "Could not create practice session.");
    } finally {
      setCreateBusy(false);
    }
  }

  const applySessionAnswers = useCallback(async (sessionId: string) => {
    try {
      const items = await listInterviewSessionAnswers(sessionId);
      const drafts: Record<string, string> = {};
      const attempts: Record<string, string> = {};
      const feedback: Record<string, InterviewAnswerAttemptResponse | undefined> = {};
      for (const item of items) {
        const qid = String(item.question_id ?? item.attempt.question_id);
        const a = item.attempt;
        drafts[qid] = a.user_answer;
        attempts[qid] = a.id;
        feedback[qid] = a;
      }
      setDraftByQuestion((prev) => ({ ...prev, ...drafts }));
      setAttemptByQuestion((prev) => ({ ...prev, ...attempts }));
      setFeedbackByQuestion((prev) => ({ ...prev, ...feedback }));
    } catch {
      /* ignore merge failures */
    }
  }, []);

  async function handleGenerate() {
    if (!practiceSession || !sourceValid) return;
    setGenerateError(null);
    setGenerateBusy(true);
    setGenerateProgress("Starting…");
    try {
      const { request_id } = await generateInterviewQuestions(practiceSession.id, {
        source,
        count,
        question_style: questionStyle,
        level: questionLevel,
        focus_detail: needsFocusDetail ? focusDetail.trim() : null,
      });
      setGenerateProgress("Generating questions…");
      const result: InterviewJobStatusResponse = await streamInterviewJobUntilDone(request_id, {
        maxWaitMs: 180_000,
      });
      if (result.status === "error") {
        throw new Error(result.error_text || "Generation failed.");
      }
      setGenerateProgress("Loading questions…");
      setQuestionsLoading(true);
      const qs = await listInterviewQuestions(practiceSession.id);
      setQuestions(qs);
      await applySessionAnswers(practiceSession.id);
    } catch (e) {
      setGenerateError(e instanceof Error ? e.message : "Generation failed.");
    } finally {
      setGenerateProgress(null);
      setGenerateBusy(false);
      setQuestionsLoading(false);
    }
  }

  async function handleSubmitAnswer(questionId: string) {
    if (!practiceSession) return;
    const text = (draftByQuestion[questionId] ?? "").trim();
    if (!text) return;
    setSubmitBusy((b) => ({ ...b, [questionId]: true }));
    try {
      const attempt = await postInterviewAnswer({
        questionId,
        practiceSessionId: practiceSession.id,
        user_answer: text,
        refine: false,
      });
      setAttemptByQuestion((m) => ({ ...m, [questionId]: attempt.id }));
      setFeedbackByQuestion((m) => ({ ...m, [questionId]: attempt }));
      setFeedbackSavedNotice((m) => ({ ...m, [questionId]: false }));
    } catch (e) {
      setFeedbackByQuestion((m) => ({
        ...m,
        [questionId]: {
          id: "",
          question_id: questionId,
          created_at: new Date().toISOString(),
          user_answer: text,
          feedback: e instanceof Error ? e.message : "Submit failed",
          refined_answer: null,
          scores_json: null,
        },
      }));
    } finally {
      setSubmitBusy((b) => ({ ...b, [questionId]: false }));
    }
  }

  async function handleGetFeedback(questionId: string) {
    if (!practiceSession) return;
    const attemptId = attemptByQuestion[questionId];
    if (!attemptId) return;
    setFeedbackSavedNotice((m) => ({ ...m, [questionId]: false }));
    setRefineBusy((b) => ({ ...b, [questionId]: true }));
    try {
      const { request_id } = await postInterviewRefine({
        answerAttemptId: attemptId,
        practiceSessionId: practiceSession.id,
      });
      const job = await streamInterviewJobUntilDone(request_id, {
        maxWaitMs: 180_000,
      });
      if (job.status === "error") {
        throw new Error(job.error_text || "Refinement failed.");
      }
      const updated = await getInterviewAnswerAttempt({
        answerAttemptId: attemptId,
        practiceSessionId: practiceSession.id,
      });
      setFeedbackByQuestion((m) => ({ ...m, [questionId]: updated }));
      setFeedbackSavedNotice((m) => ({ ...m, [questionId]: true }));
    } catch (e) {
      setFeedbackByQuestion((m) => ({
        ...m,
        [questionId]: {
          id: attemptId,
          question_id: questionId,
          created_at: new Date().toISOString(),
          user_answer: draftByQuestion[questionId] ?? "",
          feedback: e instanceof Error ? e.message : "Refinement failed",
          refined_answer: null,
          scores_json: null,
        },
      }));
      setFeedbackSavedNotice((m) => ({ ...m, [questionId]: false }));
    } finally {
      setRefineBusy((b) => ({ ...b, [questionId]: false }));
    }
  }

  const refreshHistorySessions = useCallback(async () => {
    if (!apiReady) return;
    setHistoryError(null);
    setHistoryLoading(true);
    try {
      const page = await listInterviewPracticeSessions({ limit: 100, offset: 0 });
      setHistorySessions(page.items);
      setHistoryTotal(page.total);
    } catch (e) {
      setHistoryError(e instanceof Error ? e.message : "Could not load past sessions.");
      setHistorySessions([]);
      setHistoryTotal(0);
    } finally {
      setHistoryLoading(false);
    }
  }, [apiReady]);

  useEffect(() => {
    if (mainTab === "history" && apiReady) {
      void refreshHistorySessions();
    }
  }, [mainTab, apiReady, refreshHistorySessions]);

  useEffect(() => {
    if (!selectedHistoryId || !apiReady) {
      setHistoryAnswers([]);
      return;
    }
    let cancelled = false;
    setAnswersLoading(true);
    setAnswersError(null);
    listInterviewSessionAnswers(selectedHistoryId)
      .then((rows) => {
        if (!cancelled) setHistoryAnswers(rows);
      })
      .catch((e) => {
        if (!cancelled) {
          setAnswersError(e instanceof Error ? e.message : "Could not load answers.");
          setHistoryAnswers([]);
        }
      })
      .finally(() => {
        if (!cancelled) setAnswersLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedHistoryId, apiReady]);

  async function handleContinueSession(row: InterviewPracticeSessionResponse) {
    setPracticeSession({
      id: row.id,
      resume_id: row.resume_id,
      job_description_id: row.job_description_id,
    });
    setSelResumeId(row.resume_id ?? "");
    setSelJdId(row.job_description_id ?? "");
    setMainTab("practice");
    setAttemptByQuestion({});
    setFeedbackByQuestion({});
    setDraftByQuestion({});
    setFeedbackSavedNotice({});
    try {
      localStorage.setItem(STORAGE_KEY, row.id);
    } catch {
      /* ignore */
    }
    setQuestionsLoading(true);
    try {
      const qs = await listInterviewQuestions(row.id);
      setQuestions(qs);
      await applySessionAnswers(row.id);
    } catch {
      setQuestions([]);
    } finally {
      setQuestionsLoading(false);
    }
  }

  const resumeLabel = useCallback(
    (id: string | null) => {
      if (!id) return "—";
      const r = resumes.find((x) => x.id === id);
      return r?.original_filename ?? id.slice(0, 8) + "…";
    },
    [resumes],
  );

  const jdLabel = useCallback(
    (id: string | null) => {
      if (!id) return "—";
      const j = jds.find((x) => x.id === id);
      if (!j) return id.slice(0, 8) + "…";
      const t = j.raw_text.trim().slice(0, 40);
      return t.length < j.raw_text.trim().length ? `${t}…` : t;
    },
    [jds],
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <AppPageHeader
        title="Interview practice"
        description="Generate role-specific questions from your resume and job posting, practice answers, and get feedback."
      />

      <Tabs
        value={mainTab}
        onValueChange={(v) => setMainTab(v as "practice" | "history")}
        className="flex min-h-0 flex-1 flex-col"
      >
        <div className="border-b px-4 pt-2 md:px-5">
          <TabsList variant="line" className="w-full max-w-md sm:w-fit">
            <TabsTrigger value="practice">Practice</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="practice" className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex flex-col gap-4 p-4 md:p-5">
        {connection === "offline" ? (
          <Alert variant="destructive" className="border-destructive/50">
            <AlertTitle>Can&apos;t reach the server</AlertTitle>
            <AlertDescription>
              Check that the API is running and{" "}
              <code className="text-xs">NEXT_PUBLIC_API_BASE_URL</code> is set correctly.
            </AlertDescription>
          </Alert>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>1. Choose resume and job posting</CardTitle>
            <CardDescription>
              These IDs are stored on your practice session. You need both for &quot;both&quot; mode.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {libError ? (
              <Alert variant="destructive">
                <AlertTitle>Could not load library</AlertTitle>
                <AlertDescription>{libError}</AlertDescription>
              </Alert>
            ) : null}
            {loadLibs ? (
              <div className="space-y-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label htmlFor="ip-resume" className="text-sm font-medium leading-none">
                    Resume
                  </label>
                  <Select
                    value={selResumeId || "__none__"}
                    onValueChange={(v) => setSelResumeId(v === "__none__" || v == null ? "" : v)}
                  >
                    <SelectTrigger id="ip-resume" className="w-full">
                      <SelectValue placeholder="Select a resume" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">None</SelectItem>
                      {resumes.map((r) => (
                        <SelectItem key={r.id} value={r.id}>
                          {r.original_filename ?? r.id.slice(0, 8)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label htmlFor="ip-jd" className="text-sm font-medium leading-none">
                    Job posting
                  </label>
                  <Select
                    value={selJdId || "__none__"}
                    onValueChange={(v) => setSelJdId(v === "__none__" || v == null ? "" : v)}
                  >
                    <SelectTrigger id="ip-jd" className="w-full">
                      <SelectValue placeholder="Select a job posting" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">None</SelectItem>
                      {jds.map((j) => (
                        <SelectItem key={j.id} value={j.id}>
                          {j.id.slice(0, 8)} — {j.raw_text.trim().slice(0, 48)}
                          {j.raw_text.length > 48 ? "…" : ""}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
            {createError ? (
              <p className="text-sm text-destructive">{createError}</p>
            ) : null}
            <div className="flex flex-wrap items-center gap-2">
              <Button type="button" onClick={() => void handleCreateSession()} disabled={!apiReady || createBusy}>
                {createBusy ? "Creating…" : "Create practice session"}
              </Button>
              {practiceSession ? (
                <span className="text-muted-foreground text-sm">
                  Session: <code className="text-xs">{practiceSession.id}</code>
                </span>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card className={cn(!practiceSession && "opacity-60")}>
          <CardHeader>
            <CardTitle>2. Generate questions</CardTitle>
            <CardDescription>
              Uses your worker + AI in the background. This can take a minute.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {!practiceSession ? (
              <p className="text-muted-foreground text-sm">Create a session first.</p>
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <span className="text-sm font-medium leading-none">Source</span>
                    <Select
                      value={source}
                      onValueChange={(v) => setSource(v as InterviewSource)}
                      disabled={generateBusy}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="jd" disabled={!canSourceJd}>
                          Job description only
                        </SelectItem>
                        <SelectItem value="resume" disabled={!canSourceResume}>
                          Resume only
                        </SelectItem>
                        <SelectItem value="both" disabled={!canSourceJd || !canSourceResume}>
                          Both
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="ip-count" className="text-sm font-medium leading-none">
                      Number of questions (1–25)
                    </label>
                    <Input
                      id="ip-count"
                      type="number"
                      min={1}
                      max={25}
                      value={count}
                      onChange={(e) => setCount(Math.min(25, Math.max(1, Number(e.target.value) || 8)))}
                      disabled={generateBusy}
                    />
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <span className="text-sm font-medium leading-none">Question focus</span>
                    <Select
                      value={questionStyle}
                      onValueChange={(v) => setQuestionStyle(v as InterviewQuestionStyle)}
                      disabled={generateBusy}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="random">Random mix</SelectItem>
                        <SelectItem value="technical">Technical</SelectItem>
                        <SelectItem value="behavioral">Behavioral</SelectItem>
                        <SelectItem value="domain">Specific domain</SelectItem>
                        <SelectItem value="language">Specific language</SelectItem>
                        <SelectItem value="other">Other (describe)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <span className="text-sm font-medium leading-none">Level</span>
                    <Select
                      value={questionLevel}
                      onValueChange={(v) => setQuestionLevel(v as InterviewQuestionLevel)}
                      disabled={generateBusy}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="random">Random</SelectItem>
                        <SelectItem value="easy">Easy</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="hard">Hard</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                {needsFocusDetail ? (
                  <div className="space-y-2">
                    <label htmlFor="ip-focus" className="text-sm font-medium leading-none">
                      {questionStyle === "domain"
                        ? "Domain or topic"
                        : questionStyle === "language"
                          ? "Language or stack"
                          : "What to emphasize"}
                    </label>
                    <Input
                      id="ip-focus"
                      value={focusDetail}
                      onChange={(e) => setFocusDetail(e.target.value)}
                      disabled={generateBusy}
                      placeholder={
                        questionStyle === "domain"
                          ? "e.g. healthcare, Kubernetes, payments"
                          : questionStyle === "language"
                            ? "e.g. Python, Spanish"
                            : "Describe what you want in the questions"
                      }
                    />
                    {!focusDetailValid ? (
                      <p className="text-destructive text-sm">Enter a short description to continue.</p>
                    ) : null}
                  </div>
                ) : null}
                {!sourceValid ? (
                  <p className="text-destructive text-sm">
                    This session is missing a resume or job posting for the selected source. Create a new session with
                    the right links.
                  </p>
                ) : null}
                {generateError ? <p className="text-destructive text-sm">{generateError}</p> : null}
                {generateProgress ? (
                  <p className="text-muted-foreground text-sm">{generateProgress}</p>
                ) : null}
                <Button
                  type="button"
                  onClick={() => void handleGenerate()}
                  disabled={!practiceSession || !sourceValid || generateBusy || !focusDetailValid}
                >
                  {generateBusy ? "Working…" : "Generate questions"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        <div className="space-y-3">
          <h2 className="text-lg font-semibold tracking-tight">3. Questions</h2>
          {questionsLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : questions.length === 0 ? (
            <Empty className="border border-dashed">
              <EmptyHeader>
                <EmptyTitle>No questions yet</EmptyTitle>
                <EmptyDescription>Generate questions above to start practicing.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            questions.map((q) => {
              const badges = metaLabel(q.metadata_json ?? {});
              const attemptId = attemptByQuestion[q.id];
              const fb = feedbackByQuestion[q.id];
              const hasFeedbackBlock =
                Boolean(fb?.feedback || fb?.refined_answer) ||
                Boolean(fb?.scores_json && Object.keys(fb.scores_json).length > 0);
              return (
                <Card key={q.id}>
                  <CardHeader>
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <CardTitle className="text-base leading-snug">{q.prompt}</CardTitle>
                      <div className="flex flex-wrap gap-1">
                        {badges.map((b) => (
                          <span
                            key={b}
                            className="bg-muted text-muted-foreground rounded-md px-2 py-0.5 text-xs capitalize"
                          >
                            {b}
                          </span>
                        ))}
                      </div>
                    </div>
                    <CardDescription>Source: {q.source}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-3">
                    <details className="rounded-md border bg-muted/20 p-3 text-sm">
                      <summary className="cursor-pointer font-medium">Sample answer</summary>
                      <p className="mt-2 whitespace-pre-wrap text-muted-foreground">{q.sample_answer}</p>
                    </details>
                    <div className="space-y-2">
                      <label htmlFor={`ans-${q.id}`} className="text-sm font-medium leading-none">
                        Your answer
                      </label>
                      <Textarea
                        id={`ans-${q.id}`}
                        rows={5}
                        value={draftByQuestion[q.id] ?? ""}
                        onChange={(e) =>
                          setDraftByQuestion((m) => ({
                            ...m,
                            [q.id]: e.target.value,
                          }))
                        }
                        placeholder="Type your answer…"
                        disabled={Boolean(submitBusy[q.id] || refineBusy[q.id])}
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        disabled={!practiceSession || submitBusy[q.id] || refineBusy[q.id]}
                        onClick={() => void handleSubmitAnswer(q.id)}
                      >
                        {submitBusy[q.id] ? "Saving…" : "Save answer"}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        disabled={!attemptId || refineBusy[q.id] || submitBusy[q.id]}
                        onClick={() => void handleGetFeedback(q.id)}
                      >
                        {refineBusy[q.id] ? "Getting feedback…" : "Get feedback"}
                      </Button>
                    </div>
                    {feedbackSavedNotice[q.id] ? (
                      <p className="text-muted-foreground text-sm">Feedback saved to this session.</p>
                    ) : null}
                    {hasFeedbackBlock && fb ? (
                      <div className="space-y-2 rounded-md border border-primary/20 bg-primary/5 p-3 text-sm">
                        {fb.feedback ? (
                          <div>
                            <p className="font-medium">Feedback</p>
                            <p className="mt-1 whitespace-pre-wrap text-muted-foreground">{fb.feedback}</p>
                          </div>
                        ) : null}
                        {fb.refined_answer ? (
                          <div>
                            <p className="font-medium">Refined answer</p>
                            <p className="mt-1 whitespace-pre-wrap text-muted-foreground">{fb.refined_answer}</p>
                          </div>
                        ) : null}
                        {fb.scores_json && Object.keys(fb.scores_json).length > 0 ? (
                          <pre className="mt-2 overflow-x-auto rounded bg-muted/50 p-2 text-xs">
                            {JSON.stringify(fb.scores_json, null, 2)}
                          </pre>
                        ) : null}
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
          </div>
        </TabsContent>

        <TabsContent value="history" className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex flex-col gap-4 p-4 md:p-5">
            {connection === "offline" ? (
              <Alert variant="destructive" className="border-destructive/50">
                <AlertTitle>Can&apos;t reach the server</AlertTitle>
                <AlertDescription>
                  Check that the API is running and{" "}
                  <code className="text-xs">NEXT_PUBLIC_API_BASE_URL</code> is set correctly.
                </AlertDescription>
              </Alert>
            ) : null}
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="min-h-[280px]">
                <CardHeader>
                  <CardTitle>Past sessions</CardTitle>
                  <CardDescription>
                    {historyTotal > 0 ? `${historyTotal} total` : "No sessions yet."}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex max-h-[min(60vh,28rem)] flex-col gap-2 overflow-y-auto">
                  {historyLoading ? (
                    <Skeleton className="h-24 w-full" />
                  ) : historyError ? (
                    <p className="text-destructive text-sm">{historyError}</p>
                  ) : historySessions.length === 0 ? (
                    <Empty className="border border-dashed py-8">
                      <EmptyHeader>
                        <EmptyTitle>No sessions</EmptyTitle>
                        <EmptyDescription>Create a practice session in the Practice tab.</EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  ) : (
                    historySessions.map((row) => {
                      const active = selectedHistoryId === row.id;
                      return (
                        <button
                          key={row.id}
                          type="button"
                          onClick={() => setSelectedHistoryId(row.id)}
                          className={cn(
                            "rounded-lg border p-3 text-left text-sm transition-colors outline-none select-none",
                            "hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring/50",
                            active ? "border-primary bg-primary/5" : "border-border bg-card",
                          )}
                        >
                          <p className="font-medium">{formatDateTimeUtc(row.created_at)}</p>
                          <p className="text-muted-foreground mt-1 text-xs">
                            Resume: {resumeLabel(row.resume_id)} · Job: {jdLabel(row.job_description_id)}
                          </p>
                          <p className="text-muted-foreground mt-1 font-mono text-[10px]">{row.id}</p>
                        </button>
                      );
                    })
                  )}
                </CardContent>
              </Card>

              <Card className="min-h-[280px]">
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <CardTitle>Answers in this session</CardTitle>
                      <CardDescription>
                        {selectedHistoryId
                          ? "Saved answers and coaching output."
                          : "Select a session on the left."}
                      </CardDescription>
                    </div>
                    {selectedHistoryId ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          const row = historySessions.find((s) => s.id === selectedHistoryId);
                          if (row) void handleContinueSession(row);
                        }}
                      >
                        Continue this session
                      </Button>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="max-h-[min(60vh,28rem)] flex-1 overflow-y-auto">
                  {!selectedHistoryId ? (
                    <p className="text-muted-foreground text-sm">Pick a session to see your answers.</p>
                  ) : answersLoading ? (
                    <Skeleton className="h-32 w-full" />
                  ) : answersError ? (
                    <p className="text-destructive text-sm">{answersError}</p>
                  ) : historyAnswers.length === 0 ? (
                    <p className="text-muted-foreground text-sm">No saved answers in this session yet.</p>
                  ) : (
                    <div className="flex flex-col gap-4">
                      {historyAnswers.map((item) => {
                        const a = item.attempt;
                        return (
                          <div key={a.id} className="rounded-lg border bg-muted/10 p-3 text-sm">
                            <p className="font-medium leading-snug">{item.question_prompt}</p>
                            <p className="text-muted-foreground mt-2 whitespace-pre-wrap">
                              <span className="font-medium text-foreground">Your answer: </span>
                              {a.user_answer}
                            </p>
                            {a.feedback ? (
                              <p className="mt-2 whitespace-pre-wrap">
                                <span className="font-medium">Feedback: </span>
                                {a.feedback}
                              </p>
                            ) : null}
                            {a.refined_answer ? (
                              <p className="mt-2 whitespace-pre-wrap">
                                <span className="font-medium">Refined: </span>
                                {a.refined_answer}
                              </p>
                            ) : null}
                            {a.scores_json && Object.keys(a.scores_json).length > 0 ? (
                              <pre className="mt-2 overflow-x-auto rounded bg-muted/50 p-2 text-xs">
                                {JSON.stringify(a.scores_json, null, 2)}
                              </pre>
                            ) : null}
                            <p className="text-muted-foreground mt-2 text-xs">
                              {formatDateTimeUtc(a.created_at)}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
