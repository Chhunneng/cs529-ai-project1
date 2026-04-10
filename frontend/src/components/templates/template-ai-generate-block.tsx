"use client";

import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { streamResumeTemplateGenerateLatex, type LatexAgentSseEvent } from "@/lib/api";

export function TemplateAiGenerateBlock({
  disabled,
  onApplyLatex,
  idPrefix = "template-ai",
}: {
  disabled: boolean;
  onApplyLatex: (latex: string) => void;
  idPrefix?: string;
}) {
  const [requirements, setRequirements] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamPreview, setStreamPreview] = useState("");
  const reqId = `${idPrefix}-requirements`;

  async function handleGenerate() {
    setError(null);
    const r = requirements.trim();
    if (!r) {
      setError("Describe what you want first.");
      return;
    }
    setGenerating(true);
    setStreamPreview("");
    try {
      await streamResumeTemplateGenerateLatex({ requirements: r }, (ev: LatexAgentSseEvent) => {
        if (ev.type === "text_delta") {
          setStreamPreview((prev) => prev + ev.delta);
        }
        if (ev.type === "complete") {
          onApplyLatex(ev.latex_resume_content);
        }
        if (ev.type === "error") {
          setError(ev.detail || "Generation failed.");
        }
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed.");
    } finally {
      setGenerating(false);
      setStreamPreview("");
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border/70 bg-muted/15 p-3">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        Generate from description
      </div>
      <p className="text-xs leading-relaxed text-muted-foreground">
        Describe layout, sections, and tone. The model returns full LaTeX; you can edit it before saving.
      </p>
      {error ? (
        <Alert variant="destructive" className="border-destructive/50 py-2">
          <AlertTitle className="text-sm">Generation failed</AlertTitle>
          <AlertDescription className="text-xs">{error}</AlertDescription>
        </Alert>
      ) : null}
      <Textarea
        id={reqId}
        value={requirements}
        onChange={(e) => setRequirements(e.target.value)}
        disabled={disabled || generating}
        placeholder="e.g. One-column software engineer resume with Summary, Experience, Education, Skills. Professional tone, placeholder employers."
        className="min-h-[88px] font-sans text-sm"
        aria-label="Requirements for AI LaTeX generation"
      />
      {generating && streamPreview ? (
        <pre
          className="max-h-24 overflow-auto rounded border border-border/60 bg-muted/30 p-2 font-mono text-[10px] leading-snug text-muted-foreground whitespace-pre-wrap"
          aria-live="polite"
        >
          {streamPreview}
        </pre>
      ) : null}
      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={disabled || generating}
          onClick={() => void handleGenerate()}
        >
          {generating ? "Generating…" : "Generate LaTeX"}
        </Button>
      </div>
    </div>
  );
}
