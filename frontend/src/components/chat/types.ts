export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  role: ChatRole;
  content: string;
  pdfArtifactId?: string | null;
  pdfDownloadUrl?: string | null;
};
