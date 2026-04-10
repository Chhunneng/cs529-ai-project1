"use client";

import { FileText } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ResumePdfPreview({ pdfUrl }: { pdfUrl: string | null }) {
  if (!pdfUrl) {
    return (
      <Card className="flex h-full min-h-0 flex-col border border-border/40 bg-card/80 shadow-sm ring-0 backdrop-blur-sm">
        <CardHeader className="shrink-0 border-b border-border/35 bg-muted/5 pb-3">
          <CardTitle className="flex items-center gap-2 text-base font-semibold tracking-tight">
            <FileText className="size-4 opacity-80" aria-hidden />
            Resume PDF
          </CardTitle>
          <CardDescription className="text-xs leading-relaxed">
            Send a chat message with a linked template. When the worker finishes, your latest resume
            PDF appears here.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-[200px] flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
          No PDF yet for this conversation.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden border border-border/40 bg-card/80 shadow-sm ring-0 backdrop-blur-sm">
      <CardHeader className="shrink-0 border-b border-border/35 bg-muted/5 pb-3">
        <CardTitle className="flex items-center gap-2 text-base font-semibold tracking-tight">
          <FileText className="size-4 opacity-80" aria-hidden />
          Resume PDF
        </CardTitle>
        <CardDescription className="text-xs leading-relaxed">Live preview of the latest generated PDF.</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 p-0">
        <iframe
          title="Resume PDF preview"
          src={`${pdfUrl}#toolbar=1`}
          className="h-full min-h-[320px] w-full border-0 bg-muted/20"
        />
      </CardContent>
    </Card>
  );
}
