"use client";

import { useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { resumeTemplatePreviewPdfUrl, type ResumeTemplateDetail } from "@/lib/api";

function safeJsonParse(text: string): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
  try {
    const v = JSON.parse(text) as unknown;
    if (!v || typeof v !== "object" || Array.isArray(v)) {
      return { ok: false, error: "Schema JSON must be an object." };
    }
    return { ok: true, value: v as Record<string, unknown> };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "Invalid JSON." };
  }
}

export function TemplateEditor({
  template,
  loading,
  onSave,
}: {
  template: ResumeTemplateDetail | null;
  loading: boolean;
  onSave: (args: { id: string; name: string; latex_source: string; schema_json: Record<string, unknown> }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [latex, setLatex] = useState("");
  const [schemaText, setSchemaText] = useState("{\n}\n");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadedId = template?.id ?? null;
  useMemo(() => {
    if (!template) return;
    setName(template.name ?? "");
    setLatex(template.latex_source ?? "");
    setSchemaText(JSON.stringify(template.schema_json ?? {}, null, 2));
  }, [loadedId]); // only reset editor when switching templates

  const schemaParsed = useMemo(() => safeJsonParse(schemaText), [schemaText]);

  async function handleSave() {
    if (!template) return;
    setSaveError(null);
    if (!schemaParsed.ok) {
      setSaveError(schemaParsed.error);
      return;
    }
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
      await onSave({ id: template.id, name: name.trim(), latex_source: latex, schema_json: schemaParsed.value });
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
          Paste LaTeX and schema JSON. This is what the worker uses when rendering.
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

            <div className="grid gap-4 md:grid-cols-2">
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

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Schema JSON
                  </div>
                  {!schemaParsed.ok ? (
                    <span className="text-xs text-destructive">{schemaParsed.error}</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">OK</span>
                  )}
                </div>
                <textarea
                  value={schemaText}
                  onChange={(e) => setSchemaText(e.target.value)}
                  className="min-h-[340px] w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring/25"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                disabled={loading || saving}
                onClick={() => {
                  window.open(resumeTemplatePreviewPdfUrl(template.id), "_blank", "noopener,noreferrer");
                }}
              >
                Download PDF preview
              </Button>
              <Button type="button" disabled={saving || !schemaParsed.ok} onClick={() => void handleSave()}>
                {saving ? "Saving…" : "Save template"}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

