export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  role: ChatRole;
  content: string;
  pdfArtifactId?: string | null;
  pdfDownloadUrl?: string | null;
  /** Stable key from API when loaded from history */
  id?: string;
  /** ISO timestamp for paging older messages */
  createdAt?: string;
};
