"use client";

import { useEffect, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { TemplateAiGenerateBlock } from "@/components/templates/template-ai-generate-block";
import { TemplateCompileCheckRow } from "@/components/templates/template-compile-check";
import { resumeTemplatePreviewPdfUrl, type ResumeTemplateDetail } from "@/lib/api";

export function TemplateEditor({
  template,
  loading,
  onSave,
  apiReady = true,
}: {
  template: ResumeTemplateDetail | null;
  loading: boolean;
  onSave: (args: { id: string; name: string; latex_source: string }) => Promise<void>;
  apiReady?: boolean;
}) {
  const [name, setName] = useState("");
  const [latex, setLatex] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadedId = template?.id ?? null;
  useEffect(() => {
    if (!template) return;
    setName(template.name ?? "");
    setLatex(template.latex_source ?? "");
    // Intentionally only when the selected template id changes (not on every template object refresh).
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sync fields only when switching rows
  }, [loadedId]);

  async function handleSave() {
    if (!template) return;
    setSaveError(null);
    if (!name.trim()) {
      setSaveError("Name is required.");
      return;
    }
    if (!latex.trim()) {
      setSaveError("LaTeX content is required.");
      return;
    }
    setSaving(true);
    try {
      await onSave({ id: template.id, name: name.trim(), latex_source: latex });
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
      <CardHeader className="space-y-1 border-b border-border/60 bg-muted/15">
        <CardTitle className="text-base font-semibold tracking-tight">Template editor</CardTitle>
        <CardDescription className="text-sm leading-relaxed">
          Edit the template name and LaTeX source. PDF preview compiles the LaTeX as-is.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-4">
        {loading ? (
          <Skeleton className="h-24 w-full" />
        ) : !template ? (
          <div className="text-sm text-muted-foreground">Select a template to edit.</div>
        ) : (
          <div className="flex flex-col gap-4">
            {saveError ? (
              <Alert variant="destructive" className="border-destructive/50">
                <AlertTitle>Save failed</AlertTitle>
                <AlertDescription>{saveError}</AlertDescription>
              </Alert>
            ) : null}

            <div className="flex flex-col gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Name
              </div>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="ATS Classic" />
              <div className="text-xs text-muted-foreground">ID: {template.id}</div>
            </div>

            <TemplateAiGenerateBlock
              idPrefix="template-editor-ai"
              disabled={!apiReady || loading || saving}
              onApplyLatex={(s) => setLatex(s)}
            />

            <div className="flex flex-col gap-2">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                LaTeX source
              </div>
              <textarea
                value={latex}
                onChange={(e) => setLatex(e.target.value)}
                className="min-h-[340px] w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring/25"
                placeholder="\\documentclass{...}\n..."
              />
            </div>

            <TemplateCompileCheckRow
              latex={latex}
              apiReady={apiReady}
              disabled={!apiReady || loading || saving}
              onApplyFixedLatex={(s) => setLatex(s)}
            />

            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={loading || saving}
                onClick={() => {
                  window.open(
                    resumeTemplatePreviewPdfUrl(template.id, { disposition: "inline" }),
                    "_blank",
                    "noopener,noreferrer",
                  );
                }}
              >
                Preview PDF
              </Button>
              <Button type="button" disabled={saving} onClick={() => void handleSave()}>
                {saving ? "Saving…" : "Save template"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
