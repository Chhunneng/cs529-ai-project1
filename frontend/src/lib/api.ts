import type { ChatMessage, ChatRole } from "@/components/chat/types";

const apiBaseUrl = () =>
  (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function resumeOutputPdfUrl(outputId: string): string {
  return `${apiBaseUrl()}/api/v1/resume-outputs/${encodeURIComponent(outputId)}/pdf`;
}

export function resumeTemplatePreviewPdfUrl(templateId: string): string {
  return `${apiBaseUrl()}/api/v1/resume-templates/${encodeURIComponent(templateId)}/preview-pdf`;
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
  session_id: string;
  template_id: string | null;
  status: string;
  input_json: Record<string, unknown> | null;
  tex_path: string | null;
  pdf_path: string | null;
  error_text: string | null;
  created_at: string;
  updated_at: string;
};

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
