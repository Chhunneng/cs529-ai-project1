import type { ChatMessage, ChatRole } from "@/components/chat/types";

const apiBaseUrl = () =>
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function resumeOutputPdfUrl(
  outputId: string,
  opts?: { disposition?: "inline" | "attachment" },
): string {
  const base = `${apiBaseUrl()}/api/v1/resume-outputs/${encodeURIComponent(outputId)}/pdf`;
  const disposition = opts?.disposition ?? "attachment";
  if (disposition === "attachment") {
    return base;
  }
  const q = new URLSearchParams({ disposition });
  return `${base}?${q}`;
}

/** Chat assistant PDF attachment download / preview URL. */
export function sessionPdfArtifactFileUrl(
  sessionId: string,
  artifactId: string,
  opts?: { disposition?: "inline" | "attachment" },
): string {
  const base = `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/pdf-artifacts/${encodeURIComponent(artifactId)}/file`;
  const disposition = opts?.disposition ?? "attachment";
  if (disposition === "attachment") {
    return base;
  }
  const q = new URLSearchParams({ disposition });
  return `${base}?${q}`;
}

export function resumeTemplatePreviewPdfUrl(
  templateId: string,
  opts?: { disposition?: "inline" | "attachment" },
): string {
  const base = `${apiBaseUrl()}/api/v1/resume-templates/${encodeURIComponent(templateId)}/preview-pdf`;
  const disposition = opts?.disposition ?? "attachment";
  if (disposition === "attachment") {
    return base;
  }
  const q = new URLSearchParams({ disposition });
  return `${base}?${q}`;
}

export function resumeDownloadUrl(resumeId: string): string {
  return `${apiBaseUrl()}/api/v1/resumes/${encodeURIComponent(resumeId)}/download`;
}

// —— Session ——

export type SessionResponse = {
  id: string;
  created_at: string;
  updated_at: string;
  resume_id: string | null;
  job_description_id: string | null;
  resume_template_id: string | null;
  state_json: Record<string, unknown>;
};

export type SessionPatchBody = {
  resume_id?: string | null;
  job_description_id?: string | null;
  resume_template_id?: string | null;
  state_json?: Record<string, unknown> | null;
};

// —— Resumes ——

export type ResumeListItem = {
  id: string;
  created_at: string;
  original_filename: string | null;
  mime_type: string | null;
  byte_size: number | null;
  has_file: boolean;
  parse_pending: boolean;
  parsed_json: Record<string, unknown> | null;
};

// —— Templates ——

export type ResumeTemplateListItem = {
  id: string;
  name: string;
  valid: boolean;
  created_at: string;
};

export type ResumeTemplateDetail = {
  id: string;
  name: string;
  latex_source: string;
  valid: boolean;
  created_at: string;
  updated_at?: string | null;
};

export type ResumeTemplateValidateResult = {
  ok: boolean;
  message?: string | null;
  latex_error?: string | null;
  line_number?: number | null;
  line_context?: string | null;
  hint?: string | null;
};

// —— Resume outputs ——

export type ResumeOutputResponse = {
  id: string;
  session_id: string | null;
  template_id: string | null;
  status: string;
  input_json: Record<string, unknown> | null;
  tex_path: string | null;
  pdf_path: string | null;
  error_text: string | null;
  created_at: string;
  updated_at: string;
};

export type PaginatedResumeOutputs = {
  items: ResumeOutputResponse[];
  total: number;
};

export async function listResumeOutputs(params?: {
  limit?: number;
  offset?: number;
  status?: string | null;
}): Promise<PaginatedResumeOutputs> {
  const q = new URLSearchParams();
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  if (params?.status?.trim()) q.set("status", params.status.trim());
  const qs = q.toString();
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-outputs${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new Error(`listResumeOutputs failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PaginatedResumeOutputs;
}

export type PdfArtifactListItem = {
  id: string;
  session_id: string;
  mime_type: string;
  created_at: string;
};

export type PaginatedPdfArtifacts = {
  items: PdfArtifactListItem[];
  total: number;
};

export async function listPdfArtifacts(params?: {
  limit?: number;
  offset?: number;
}): Promise<PaginatedPdfArtifacts> {
  const q = new URLSearchParams();
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  const res = await fetch(`${apiBaseUrl()}/api/v1/pdf-artifacts${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new Error(`listPdfArtifacts failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PaginatedPdfArtifacts;
}

export async function deleteResumeOutput(outputId: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-outputs/${encodeURIComponent(outputId)}`, {
    method: "DELETE",
  });
  if (res.status === 409) {
    throw new Error(`deleteResumeOutput conflict (409): ${await readErrorBody(res)}`);
  }
  if (!res.ok) {
    throw new Error(`deleteResumeOutput failed ${res.status}: ${await readErrorBody(res)}`);
  }
}

export async function deleteSessionPdfArtifact(sessionId: string, artifactId: string): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/pdf-artifacts/${encodeURIComponent(artifactId)}`,
    { method: "DELETE" },
  );
  if (!res.ok) {
    throw new Error(`deleteSessionPdfArtifact failed ${res.status}: ${await readErrorBody(res)}`);
  }
}

// —— Job descriptions ——

export type JobDescriptionResponse = {
  id: string;
  raw_text: string;
  extracted_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

// —— Chat ——

export type ApiChatRow = {
  id: string;
  session_id: string;
  role: string;
  content: string;
  sequence: number;
  created_at: string;
  pdf_artifact_id?: string | null;
  pdf_download_url?: string | null;
};

export type AssistantStreamEvent =
  | { type: "assistant"; message: ApiChatRow }
  | { type: "timeout"; detail?: string }
  | { type: "error"; detail?: string };

export type PendingRepliesResponse = {
  pending_user_message_ids: string[];
};

export async function getSessionPendingReplies(sessionId: string): Promise<PendingRepliesResponse> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/messages/pending-replies`,
  );
  if (!res.ok) {
    throw new Error(`getSessionPendingReplies failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PendingRepliesResponse;
}

export function apiChatRowToChatMessage(row: ApiChatRow): ChatMessage {
  const role: ChatRole =
    row.role === "user" || row.role === "assistant" ? row.role : "assistant";
  const rel = row.pdf_download_url?.trim();
  const pdfDownloadUrl = rel && rel.length > 0 ? `${apiBaseUrl()}${rel}` : undefined;
  return {
    role,
    content: row.content,
    pdfArtifactId: row.pdf_artifact_id ?? undefined,
    pdfDownloadUrl,
    id: row.id,
    createdAt: row.created_at,
  };
}

async function readErrorBody(res: Response): Promise<string> {
  try {
    const text = await res.text();
    return text.slice(0, 500);
  } catch {
    return "";
  }
}

export async function pingBackend(): Promise<boolean> {
  try {
    const res = await fetch(`${apiBaseUrl()}/healthz`);
    return res.ok;
  } catch {
    return false;
  }
}

export type PaginatedSessions = { items: SessionResponse[]; total: number };

export async function listSessions(params?: {
  limit?: number;
  offset?: number;
}): Promise<PaginatedSessions> {
  const q = new URLSearchParams();
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  const res = await fetch(`${apiBaseUrl()}/api/v1/sessions${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new Error(`listSessions failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PaginatedSessions;
}

export async function createSession(): Promise<{ id: string }> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/sessions`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`createSession failed ${res.status}: ${await readErrorBody(res)}`);
  }
  const data = (await res.json()) as { id: string };
  return { id: String(data.id) };
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (res.status === 404) {
    throw new Error(`deleteSession: session not found`);
  }
  if (!res.ok) {
    throw new Error(`deleteSession failed ${res.status}: ${await readErrorBody(res)}`);
  }
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}`);
  if (!res.ok) {
    throw new Error(`getSession failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as SessionResponse;
}

export async function patchSession(
  sessionId: string,
  body: SessionPatchBody,
): Promise<SessionResponse> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`patchSession failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as SessionResponse;
}

export type PaginatedResumes = { items: ResumeListItem[]; total: number };

export async function listResumes(params?: {
  limit?: number;
  offset?: number;
  q?: string;
}): Promise<PaginatedResumes> {
  const sp = new URLSearchParams();
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.offset != null) sp.set("offset", String(params.offset));
  if (params?.q?.trim()) sp.set("q", params.q.trim());
  const qs = sp.toString();
  const res = await fetch(`${apiBaseUrl()}/api/v1/resumes${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new Error(`listResumes failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PaginatedResumes;
}

function filenameFromContentDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const utf8 = /filename\*=UTF-8''([^;\n]+)/i.exec(header);
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1].trim().replace(/^["']|["']$/g, ""));
    } catch {
      /* use fallback below */
    }
  }
  const quoted = /filename="([^"\n]+)"/i.exec(header);
  if (quoted?.[1]) return quoted[1].trim();
  const plain = /filename=([^;\n]+)/i.exec(header);
  if (plain?.[1]) return plain[1].trim().replace(/^["']|["']$/g, "");
  return fallback;
}

export async function uploadResume(file: File): Promise<ResumeListItem> {
  const body = new FormData();
  body.append("file", file);
  const res = await fetch(`${apiBaseUrl()}/api/v1/resumes`, {
    method: "POST",
    body,
  });
  if (!res.ok) {
    let detail = await readErrorBody(res);
    try {
      const j = JSON.parse(detail) as { detail?: unknown };
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail))
        detail = j.detail.map((x) => (typeof x === "object" && x && "msg" in x ? String((x as { msg: string }).msg) : String(x))).join("; ");
    } catch {
      /* keep detail */
    }
    throw new Error(`uploadResume failed ${res.status}: ${detail}`);
  }
  return (await res.json()) as ResumeListItem;
}

export async function downloadFileFromUrl(url: string, fallbackFilename: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`download failed ${res.status}: ${await readErrorBody(res)}`);
  }
  const blob = await res.blob();
  const name = filenameFromContentDisposition(
    res.headers.get("Content-Disposition"),
    fallbackFilename || "download",
  );
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}

export async function downloadResumeFile(resumeId: string, fallbackFilename: string): Promise<void> {
  return downloadFileFromUrl(resumeDownloadUrl(resumeId), fallbackFilename || "resume");
}

export async function getResume(resumeId: string): Promise<ResumeListItem> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resumes/${encodeURIComponent(resumeId)}`);
  if (!res.ok) {
    throw new Error(`getResume failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeListItem;
}

export async function deleteResume(resumeId: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resumes/${encodeURIComponent(resumeId)}`, {
    method: "DELETE",
  });
  if (res.status === 404) {
    throw new Error("Resume not found.");
  }
  if (!res.ok) {
    throw new Error(`deleteResume failed ${res.status}: ${await readErrorBody(res)}`);
  }
}

export type PaginatedResumeTemplates = { items: ResumeTemplateListItem[]; total: number };

export async function listResumeTemplates(params?: {
  limit?: number;
  offset?: number;
  q?: string;
}): Promise<PaginatedResumeTemplates> {
  const sp = new URLSearchParams();
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.offset != null) sp.set("offset", String(params.offset));
  if (params?.q?.trim()) sp.set("q", params.q.trim());
  const qs = sp.toString();
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-templates${qs ? `?${qs}` : ""}`);
  if (!res.ok) {
    throw new Error(`listResumeTemplates failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PaginatedResumeTemplates;
}

export async function getResumeTemplate(templateId: string): Promise<ResumeTemplateDetail> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/resume-templates/${encodeURIComponent(templateId)}`,
  );
  if (!res.ok) {
    throw new Error(`getResumeTemplate failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeTemplateDetail;
}

export async function createResumeTemplate(body: {
  name: string;
  latex_source: string;
}): Promise<ResumeTemplateDetail> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-templates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: body.name,
      latex_source: body.latex_source,
    }),
  });
  if (!res.ok) {
    throw new Error(`createResumeTemplate failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeTemplateDetail;
}

/** SSE payloads from POST /resume-templates/generate-latex and /fix-latex */
export type LatexAgentSseEvent =
  | { type: "item"; name: string }
  | { type: "agent"; name: string }
  | { type: "text_delta"; delta: string }
  | { type: "complete"; latex_resume_content: string }
  | { type: "error"; detail: string };

function flushSseBuffer(
  buffer: string,
  onDataPayload: (payload: string) => void,
): string {
  let rest = buffer;
  let sep: number;
  while ((sep = rest.indexOf("\n\n")) >= 0) {
    const block = rest.slice(0, sep);
    rest = rest.slice(sep + 2);
    for (const rawLine of block.split("\n")) {
      const line = rawLine.trimEnd();
      if (line.startsWith("data:")) {
        const payload = line.slice(5).trimStart();
        if (payload) onDataPayload(payload);
      }
    }
  }
  return rest;
}

async function postResumeTemplateLatexSse(
  path: "/generate-latex" | "/fix-latex",
  jsonBody: Record<string, unknown>,
  errorPrefix: string,
  onEvent: (ev: LatexAgentSseEvent) => void,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-templates${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(jsonBody),
  });
  if (!res.ok) {
    throw new Error(`${errorPrefix} failed ${res.status}: ${await readErrorBody(res)}`);
  }
  const reader = res.body?.getReader();
  if (!reader) {
    throw new Error(`${errorPrefix}: no response body`);
  }
  const decoder = new TextDecoder();
  let buffer = "";
  let terminal: "complete" | "error" | null = null;

  const dispatch = (payload: string) => {
    let ev: LatexAgentSseEvent;
    try {
      ev = JSON.parse(payload) as LatexAgentSseEvent;
    } catch {
      ev = { type: "error", detail: "invalid_stream_payload" };
    }
    onEvent(ev);
    if (ev.type === "complete" || ev.type === "error") terminal = ev.type;
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = flushSseBuffer(buffer, dispatch);
  }
  buffer = flushSseBuffer(`${buffer}\n\n`, dispatch);

  if (!terminal) {
    throw new Error(`${errorPrefix}: stream ended without a complete or error event.`);
  }
}

export async function streamResumeTemplateGenerateLatex(
  body: { requirements: string },
  onEvent: (ev: LatexAgentSseEvent) => void,
): Promise<void> {
  await postResumeTemplateLatexSse(
    "/generate-latex",
    { requirements: body.requirements },
    "generateResumeTemplateLatex",
    onEvent,
  );
}

export async function streamResumeTemplateFixLatex(
  body: { latex_source: string; error_message: string },
  onEvent: (ev: LatexAgentSseEvent) => void,
): Promise<void> {
  await postResumeTemplateLatexSse(
    "/fix-latex",
    { latex_source: body.latex_source, error_message: body.error_message },
    "fixResumeTemplateLatex",
    onEvent,
  );
}

export async function validateResumeTemplateLatex(body: {
  latex_source: string;
}): Promise<ResumeTemplateValidateResult> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-templates/validate-latex`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ latex_source: body.latex_source }),
  });
  if (!res.ok) {
    throw new Error(`validateResumeTemplateLatex failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeTemplateValidateResult;
}

export async function patchResumeTemplate(
  templateId: string,
  body: {
    name?: string | null;
    latex_source?: string | null;
  },
): Promise<ResumeTemplateDetail> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-templates/${encodeURIComponent(templateId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`patchResumeTemplate failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeTemplateDetail;
}

export async function deleteResumeTemplate(templateId: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-templates/${encodeURIComponent(templateId)}`, {
    method: "DELETE",
  });
  if (res.status === 404) {
    throw new Error("Template not found.");
  }
  if (!res.ok) {
    throw new Error(`deleteResumeTemplate failed ${res.status}: ${await readErrorBody(res)}`);
  }
}

export async function createResumeOutput(
  sessionId: string,
  body: {
    template_id: string;
    source_resume_id?: string | null;
    job_description_id?: string | null;
  },
): Promise<ResumeOutputResponse> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/resume-outputs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        template_id: body.template_id,
        source_resume_id: body.source_resume_id ?? null,
        job_description_id: body.job_description_id ?? null,
      }),
    },
  );
  if (!res.ok) {
    throw new Error(`createResumeOutput failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeOutputResponse;
}

/** Session-free ATS PDF: template + resume + job description (all required). */
export async function createStandaloneResumeOutput(body: {
  template_id: string;
  source_resume_id: string;
  job_description_id: string;
}): Promise<ResumeOutputResponse> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/resume-outputs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      template_id: body.template_id,
      source_resume_id: body.source_resume_id,
      job_description_id: body.job_description_id,
    }),
  });
  if (!res.ok) {
    throw new Error(`createStandaloneResumeOutput failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeOutputResponse;
}

export async function createJobDescription(params: {
  session_id: string;
  raw_text: string;
  set_active?: boolean;
}): Promise<JobDescriptionResponse> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(params.session_id)}/job-descriptions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_text: params.raw_text,
        set_active: params.set_active ?? true,
      }),
    },
  );
  if (!res.ok) {
    throw new Error(`createJobDescription failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as JobDescriptionResponse;
}

/** Save a posting to the shared library only (no chat session). */
export async function createJobDescriptionLibrary(raw_text: string): Promise<JobDescriptionResponse> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/job-descriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_text, set_active: false }),
  });
  if (!res.ok) {
    throw new Error(`createJobDescriptionLibrary failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as JobDescriptionResponse;
}

export type PaginatedJobDescriptions = { items: JobDescriptionResponse[]; total: number };

export async function listJobDescriptions(params?: {
  limit?: number;
  offset?: number;
}): Promise<PaginatedJobDescriptions> {
  const q = new URLSearchParams();
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/job-descriptions${qs ? `?${qs}` : ""}`,
  );
  if (!res.ok) {
    throw new Error(`listJobDescriptions failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PaginatedJobDescriptions;
}

export async function getJobDescription(jobDescriptionId: string): Promise<JobDescriptionResponse> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/job-descriptions/${encodeURIComponent(jobDescriptionId)}`,
  );
  if (!res.ok) {
    throw new Error(`getJobDescription failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as JobDescriptionResponse;
}

export async function activateJobDescription(params: {
  session_id: string;
  job_description_id: string;
}): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(params.session_id)}/job-descriptions/${encodeURIComponent(params.job_description_id)}/activate`,
    { method: "POST" },
  );
  if (!res.ok) {
    throw new Error(`activateJobDescription failed ${res.status}: ${await readErrorBody(res)}`);
  }
}

export async function getResumeOutput(outputId: string): Promise<ResumeOutputResponse> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/resume-outputs/${encodeURIComponent(outputId)}`,
  );
  if (!res.ok) {
    throw new Error(`getResumeOutput failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ResumeOutputResponse;
}

export async function listSessionMessages(
  sessionId: string,
  params?: { limit?: number; before?: string; anchor?: "start" | "end" },
): Promise<ChatMessage[]> {
  const q = new URLSearchParams();
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.before) q.set("before", params.before);
  if (params?.anchor) q.set("anchor", params.anchor);
  const qs = q.toString();
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/messages${qs ? `?${qs}` : ""}`,
  );
  if (!res.ok) {
    throw new Error(`listSessionMessages failed ${res.status}: ${await readErrorBody(res)}`);
  }
  const rows = (await res.json()) as ApiChatRow[];
  return rows.map(apiChatRowToChatMessage);
}

export async function postSessionMessage(params: {
  sessionId: string;
  content: string;
  resume_template_id: string;
  resume_id: string;
  job_description_id: string;
}): Promise<ApiChatRow> {
  const body = {
    content: params.content,
    resume_template_id: params.resume_template_id,
    resume_id: params.resume_id,
    job_description_id: params.job_description_id,
  };

  const res = await fetch(
    `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(params.sessionId)}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) {
    throw new Error(`postSessionMessage failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as ApiChatRow;
}

/** @deprecated Use postSessionMessage with full session link IDs */
export async function postChatMessage(params: {
  session_id: string;
  message: string;
  resume_template_id: string;
  resume_id: string;
  job_description_id: string;
}): Promise<ApiChatRow> {
  return postSessionMessage({
    sessionId: params.session_id,
    content: params.message,
    resume_template_id: params.resume_template_id,
    resume_id: params.resume_id,
    job_description_id: params.job_description_id,
  });
}

/** Server-Sent Events: one `message` event with JSON body, then connection closes. */
export function openAssistantReplyStream(
  sessionId: string,
  userMessageId: string,
  handlers: {
    onEvent: (event: AssistantStreamEvent) => void;
    onTransportError?: () => void;
  },
): EventSource {
  const q = new URLSearchParams({ user_message_id: userMessageId });
  const url = `${apiBaseUrl()}/api/v1/sessions/${encodeURIComponent(sessionId)}/messages/assistant-stream?${q}`;
  const es = new EventSource(url);
  let finished = false;

  const finish = () => {
    if (finished) return;
    finished = true;
    es.close();
  };

  es.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data) as AssistantStreamEvent;
      handlers.onEvent(data);
    } catch {
      handlers.onEvent({ type: "error", detail: "invalid_stream_payload" });
    }
    finish();
  };

  es.onerror = () => {
    if (!finished) {
      handlers.onTransportError?.();
    }
    finish();
  };

  return es;
}

// —— Interview practice ——

export type InterviewSource = "jd" | "resume" | "both";
export type InterviewQuestionStyle =
  | "random"
  | "technical"
  | "behavioral"
  | "domain"
  | "language"
  | "other";
export type InterviewQuestionLevel = "random" | "easy" | "medium" | "hard";
export type InterviewJobKind = "generate" | "refine";
export type InterviewJobStatus = "pending" | "running" | "done" | "error";

export type InterviewPracticeSessionResponse = {
  id: string;
  created_at: string;
  updated_at: string;
  resume_id: string | null;
  job_description_id: string | null;
};

export type InterviewQuestionResponse = {
  id: string;
  practice_session_id: string;
  created_at: string;
  source: InterviewSource;
  prompt: string;
  sample_answer: string;
  metadata_json: Record<string, unknown>;
};

export type InterviewGenerateEnqueueResponse = {
  request_id: string;
};

export type InterviewJobStatusResponse = {
  id: string;
  practice_session_id: string;
  kind: InterviewJobKind;
  status: InterviewJobStatus;
  created_at: string;
  updated_at: string;
  error_text: string | null;
  result_json: Record<string, unknown> | null;
};

export type InterviewAnswerAttemptResponse = {
  id: string;
  question_id: string;
  created_at: string;
  user_answer: string;
  feedback: string | null;
  refined_answer: string | null;
  scores_json: Record<string, unknown> | null;
};

export type InterviewRefineEnqueueResponse = {
  request_id: string;
  answer_attempt_id: string;
};

export async function createInterviewPracticeSession(body: {
  resume_id?: string | null;
  job_description_id?: string | null;
}): Promise<InterviewPracticeSessionResponse> {
  const res = await fetch(`${apiBaseUrl()}/api/v1/interview-practice/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resume_id: body.resume_id ?? null,
      job_description_id: body.job_description_id ?? null,
    }),
  });
  if (!res.ok) {
    throw new Error(`createInterviewPracticeSession failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewPracticeSessionResponse;
}

export async function generateInterviewQuestions(
  practiceSessionId: string,
  body: {
    source: InterviewSource;
    count?: number;
    question_style?: InterviewQuestionStyle;
    level?: InterviewQuestionLevel;
    focus_detail?: string | null;
  },
): Promise<InterviewGenerateEnqueueResponse> {
  const payload: Record<string, unknown> = {
    source: body.source,
    count: body.count ?? 8,
    question_style: body.question_style ?? "random",
    level: body.level ?? "random",
  };
  if (body.focus_detail != null && String(body.focus_detail).trim() !== "") {
    payload.focus_detail = String(body.focus_detail).trim();
  }
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/sessions/${encodeURIComponent(practiceSessionId)}/generate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!res.ok) {
    throw new Error(`generateInterviewQuestions failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewGenerateEnqueueResponse;
}

export async function listInterviewQuestions(
  practiceSessionId: string,
): Promise<InterviewQuestionResponse[]> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/sessions/${encodeURIComponent(practiceSessionId)}/questions`,
  );
  if (!res.ok) {
    throw new Error(`listInterviewQuestions failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewQuestionResponse[];
}

export async function getInterviewJobRequest(requestId: string): Promise<InterviewJobStatusResponse> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/requests/${encodeURIComponent(requestId)}`,
  );
  if (!res.ok) {
    throw new Error(`getInterviewJobRequest failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewJobStatusResponse;
}

/** Wait for generate/refine job completion via SSE (no client polling). */
export async function streamInterviewJobUntilDone(
  requestId: string,
  opts?: { signal?: AbortSignal; maxWaitMs?: number },
): Promise<InterviewJobStatusResponse> {
  const maxWaitMs = opts?.maxWaitMs ?? 300_000;
  const url = `${apiBaseUrl()}/api/v1/interview-practice/requests/${encodeURIComponent(requestId)}/stream`;
  const controller = new AbortController();
  const onParentAbort = () => controller.abort();
  opts?.signal?.addEventListener("abort", onParentAbort);
  const timer = setTimeout(() => controller.abort(), maxWaitMs);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) {
      throw new Error(`streamInterviewJobUntilDone failed ${res.status}: ${await readErrorBody(res)}`);
    }
    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error("streamInterviewJobUntilDone: empty response body");
    }
    const decoder = new TextDecoder();
    let buffer = "";
    let lastJob: InterviewJobStatusResponse | null = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const block of parts) {
        for (const line of block.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          let payload: Record<string, unknown>;
          try {
            payload = JSON.parse(line.slice(6)) as Record<string, unknown>;
          } catch {
            continue;
          }
          const eventType = payload.type;
          if (eventType === "snapshot" || eventType === "update") {
            const job = payload.job as InterviewJobStatusResponse;
            lastJob = job;
            if (job.status === "done" || job.status === "error") {
              return job;
            }
          }
          if (eventType === "error") {
            throw new Error(String(payload.detail ?? "Interview job stream error"));
          }
          if (eventType === "timeout") {
            throw new Error(String(payload.detail ?? "Interview job wait timed out"));
          }
        }
      }
    }
    if (lastJob && (lastJob.status === "done" || lastJob.status === "error")) {
      return lastJob;
    }
    throw new Error("Interview job stream ended before completion");
  } finally {
    clearTimeout(timer);
    opts?.signal?.removeEventListener("abort", onParentAbort);
  }
}

export async function postInterviewAnswer(params: {
  questionId: string;
  practiceSessionId: string;
  user_answer: string;
  refine?: boolean;
}): Promise<InterviewAnswerAttemptResponse> {
  const q = new URLSearchParams({ practice_session_id: params.practiceSessionId });
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/questions/${encodeURIComponent(params.questionId)}/answers?${q}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_answer: params.user_answer,
        refine: params.refine ?? false,
      }),
    },
  );
  if (!res.ok) {
    throw new Error(`postInterviewAnswer failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewAnswerAttemptResponse;
}

export async function postInterviewRefine(params: {
  answerAttemptId: string;
  practiceSessionId: string;
}): Promise<InterviewRefineEnqueueResponse> {
  const q = new URLSearchParams({ practice_session_id: params.practiceSessionId });
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/answers/${encodeURIComponent(params.answerAttemptId)}/refine?${q}`,
    { method: "POST" },
  );
  if (!res.ok) {
    throw new Error(`postInterviewRefine failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewRefineEnqueueResponse;
}

export async function getInterviewAnswerAttempt(params: {
  answerAttemptId: string;
  practiceSessionId: string;
}): Promise<InterviewAnswerAttemptResponse> {
  const q = new URLSearchParams({ practice_session_id: params.practiceSessionId });
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/answers/${encodeURIComponent(params.answerAttemptId)}?${q}`,
  );
  if (!res.ok) {
    throw new Error(`getInterviewAnswerAttempt failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewAnswerAttemptResponse;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function pollInterviewJobRequest(
  requestId: string,
  opts?: { intervalMs?: number; maxWaitMs?: number; signal?: AbortSignal },
): Promise<InterviewJobStatusResponse> {
  const intervalMs = opts?.intervalMs ?? 1000;
  const maxWaitMs = opts?.maxWaitMs ?? 120_000;
  const started = Date.now();

  while (true) {
    if (opts?.signal?.aborted) {
      throw new Error("pollInterviewJobRequest aborted");
    }
    const row = await getInterviewJobRequest(requestId);
    if (row.status === "done" || row.status === "error") {
      return row;
    }
    if (Date.now() - started > maxWaitMs) {
      throw new Error("pollInterviewJobRequest: timed out waiting for job to finish");
    }
    await sleep(intervalMs);
  }
}

export type PaginatedInterviewPracticeSessions = {
  items: InterviewPracticeSessionResponse[];
  total: number;
};

export async function listInterviewPracticeSessions(params?: {
  limit?: number;
  offset?: number;
}): Promise<PaginatedInterviewPracticeSessions> {
  const q = new URLSearchParams();
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const qs = q.toString();
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/sessions${qs ? `?${qs}` : ""}`,
  );
  if (!res.ok) {
    throw new Error(`listInterviewPracticeSessions failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as PaginatedInterviewPracticeSessions;
}

export type InterviewAnswerHistoryItem = {
  question_id: string;
  question_prompt: string;
  attempt: InterviewAnswerAttemptResponse;
};

export async function listInterviewSessionAnswers(
  practiceSessionId: string,
): Promise<InterviewAnswerHistoryItem[]> {
  const res = await fetch(
    `${apiBaseUrl()}/api/v1/interview-practice/sessions/${encodeURIComponent(practiceSessionId)}/answers`,
  );
  if (!res.ok) {
    throw new Error(`listInterviewSessionAnswers failed ${res.status}: ${await readErrorBody(res)}`);
  }
  return (await res.json()) as InterviewAnswerHistoryItem[];
}
