import type {
  JobDescriptionResponse,
  ResumeListItem,
  ResumeTemplateListItem,
  SessionResponse,
} from "@/lib/api";

/** Sentinel for “no selection” in Selects (must match SelectItem value). */
export const SELECT_NONE = "__none__";
export const SELECT_NONE_JOB = "__jd_none__";

/** Job postings list: show every saved JD (not a session id). */
export const JD_FILTER_ALL = "__jd_filter_all__";

export function labelResumeSelectValue(
  value: unknown,
  resumes: ResumeListItem[],
  noneSentinel: string = SELECT_NONE,
): string {
  if (value === noneSentinel || value == null || value === "") {
    return "No resume selected";
  }
  const id = String(value);
  const r = resumes.find((x) => x.id === id);
  if (!r) return `${id.slice(0, 8)}…`;
  const name = r.original_filename?.trim() || `${r.id.slice(0, 8)}…`;
  return `${name} (${new Date(r.created_at).toLocaleDateString()})`;
}

export function labelJobSelectValue(
  value: unknown,
  jds: JobDescriptionResponse[],
  noneSentinel: string = SELECT_NONE_JOB,
): string {
  if (value === noneSentinel || value == null || value === "") {
    return "No job description selected";
  }
  const id = String(value);
  const jd = jds.find((x) => x.id === id);
  if (!jd) return `${id.slice(0, 8)}…`;
  return `${id.slice(0, 8)}… (${new Date(jd.created_at).toLocaleDateString()})`;
}

export function labelTemplateSelectValue(
  value: unknown,
  templates: ResumeTemplateListItem[],
  noneSentinel: string = SELECT_NONE,
): string {
  if (value === noneSentinel || value == null || value === "") {
    return "No template selected";
  }
  const id = String(value);
  const t = templates.find((x) => x.id === id);
  return t?.name ?? `Template ${id.slice(0, 8)}…`;
}

export function labelSessionSelectValue(value: unknown, sessions: SessionResponse[]): string {
  if (value === SELECT_NONE || value == null || value === "") {
    return "No session selected";
  }
  const id = String(value);
  const s = sessions.find((x) => x.id === id);
  if (!s) return `${id.slice(0, 8)}…`;
  return `${id.slice(0, 8)}… (${new Date(s.created_at).toLocaleDateString()})`;
}

export function labelJdListFilterValue(
  value: unknown,
  sessions: SessionResponse[],
  allSentinel: string = JD_FILTER_ALL,
): string {
  if (value === allSentinel || value == null || value === "") {
    return "All postings";
  }
  const id = String(value);
  const s = sessions.find((x) => x.id === id);
  if (!s) return `Active in chat ${id.slice(0, 8)}…`;
  return `Active in ${id.slice(0, 8)}… (${new Date(s.created_at).toLocaleDateString()})`;
}
