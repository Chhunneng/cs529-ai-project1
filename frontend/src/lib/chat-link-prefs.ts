import type { SessionPatchBody, SessionResponse } from "@/lib/api";

const STORAGE_KEY = "resume-agent:last-chat-links";
const VERSION = 1;

export type StoredChatLinksV1 = {
  v: typeof VERSION;
  resume_id: string | null;
  job_description_id: string | null;
  resume_template_id: string | null;
};

function emptyLinks(): StoredChatLinksV1 {
  return {
    v: VERSION,
    resume_id: null,
    job_description_id: null,
    resume_template_id: null,
  };
}

/** Read persisted last chat links, or null if missing/invalid. */
export function readLastChatLinks(): StoredChatLinksV1 | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as unknown;
    if (!data || typeof data !== "object") return null;
    const o = data as Record<string, unknown>;
    if (o.v !== VERSION) return null;
    return {
      v: VERSION,
      resume_id: typeof o.resume_id === "string" && o.resume_id.length > 0 ? o.resume_id : null,
      job_description_id:
        typeof o.job_description_id === "string" && o.job_description_id.length > 0
          ? o.job_description_id
          : null,
      resume_template_id:
        typeof o.resume_template_id === "string" && o.resume_template_id.length > 0
          ? o.resume_template_id
          : null,
    };
  } catch {
    return null;
  }
}

function writeStored(links: StoredChatLinksV1): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(links));
}

/** Replace stored links (use sparingly). */
export function writeLastChatLinks(partial: Partial<Omit<StoredChatLinksV1, "v">>): void {
  try {
    const prev = readLastChatLinks() ?? emptyLinks();
    writeStored({
      v: VERSION,
      resume_id: partial.resume_id !== undefined ? partial.resume_id : prev.resume_id,
      job_description_id:
        partial.job_description_id !== undefined ? partial.job_description_id : prev.job_description_id,
      resume_template_id:
        partial.resume_template_id !== undefined ? partial.resume_template_id : prev.resume_template_id,
    });
  } catch {
    /* ignore quota / private mode */
  }
}

/**
 * Merge non-null link fields from a session row into storage; null on the session keeps the
 * previous stored value for that field (sticky defaults for new chats).
 */
export function mergeFromSession(session: SessionResponse): void {
  try {
    const prev = readLastChatLinks() ?? emptyLinks();
    writeStored({
      v: VERSION,
      resume_id: session.resume_id ?? prev.resume_id,
      job_description_id: session.job_description_id ?? prev.job_description_id,
      resume_template_id: session.resume_template_id ?? prev.resume_template_id,
    });
  } catch {
    /* ignore */
  }
}

/** Build a PATCH body from stored prefs (only keys that are set). */
export function sessionPatchBodyFromStored(): SessionPatchBody | null {
  const p = readLastChatLinks();
  if (!p) return null;
  const body: SessionPatchBody = {};
  if (p.resume_id) body.resume_id = p.resume_id;
  if (p.job_description_id) body.job_description_id = p.job_description_id;
  if (p.resume_template_id) body.resume_template_id = p.resume_template_id;
  if (Object.keys(body).length === 0) return null;
  return body;
}
