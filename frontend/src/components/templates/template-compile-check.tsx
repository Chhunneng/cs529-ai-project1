"use client";

import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  streamResumeTemplateFixLatex,
  validateResumeTemplateLatex,
  type LatexAgentSseEvent,
  type ResumeTemplateValidateResult,
} from "@/lib/api";

function buildErrorContextForFix(r: ResumeTemplateValidateResult): string {
  const parts: string[] = [];
  if (r.message) parts.push(r.message);
  if (r.latex_error) parts.push(`LaTeX error: ${r.latex_error}`);
  if (r.line_number != null) parts.push(`Line: ${r.line_number}`);
  if (r.hint) parts.push(`Hint: ${r.hint}`);
  if (r.line_context) parts.push(`Source context:\n${r.line_context}`);
  return parts.join("\n\n").trim() || "Compile check failed (no details).";
}

export function TemplateCompileCheckRow({
  latex,
  disabled,
  apiReady = true,
  onApplyFixedLatex,
}: {
  latex: string;
  disabled: boolean;
  apiReady?: boolean;
  onApplyFixedLatex?: (fixed: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [fixing, setFixing] = useState(false);
  const [result, setResult] = useState<ResumeTemplateValidateResult | null>(null);
  const [fixError, setFixError] = useState<string | null>(null);

  async function check() {
    setResult(null);
    setFixError(null);
    const t = latex.trim();
    if (!t) {
      setResult({ ok: false, message: "Add some LaTeX first, then check." });
      return;
    }
    setLoading(true);
    try {
      const r = await validateResumeTemplateLatex({ latex_source: t });
      setResult(r);
    } catch (e) {
      setResult({
        ok: false,
        message: e instanceof Error ? e.message : "Could not reach the server.",
      });
    } finally {
      setLoading(false);
    }
  }

  async function fixWithAi() {
    setFixError(null);
    const t = latex.trim();
    if (!t || !result || result.ok) return;
    const errText = buildErrorContextForFix(result);
    setFixing(true);
    try {
      await streamResumeTemplateFixLatex(
        {
          latex_source: t,
          error_message: errText,
        },
        (ev: LatexAgentSseEvent) => {
          if (ev.type === "complete") {
            onApplyFixedLatex?.(ev.latex_resume_content);
          }
          if (ev.type === "error") {
            setFixError(ev.detail || "Fix failed.");
          }
        },
      );
    } catch (e) {
      setFixError(e instanceof Error ? e.message : "Fix request failed.");
    } finally {
      setFixing(false);
    }
  }

  const canFix = Boolean(onApplyFixedLatex) && apiReady && result && !result.ok;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-fit"
          disabled={disabled || loading || fixing}
          onClick={() => void check()}
        >
          {loading ? "Checking compile…" : "Check LaTeX compile"}
        </Button>
        {canFix ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            className="w-fit"
            disabled={disabled || loading || fixing}
            onClick={() => void fixWithAi()}
          >
            {fixing ? "Fixing…" : "Fix with AI"}
          </Button>
        ) : null}
      </div>
      {fixError ? (
        <p className="text-xs text-destructive leading-relaxed">{fixError}</p>
      ) : null}
      {result ? (
        <Alert
          variant={result.ok ? "default" : "destructive"}
          className={result.ok ? "border-border/80 bg-muted/20" : "border-destructive/50"}
        >
          <AlertTitle className="text-sm">
            {result.ok ? "Compiles" : "Does not compile"}
          </AlertTitle>
          <AlertDescription className="space-y-1 text-xs leading-relaxed">
            {result.message ? <p>{result.message}</p> : null}
            {!result.ok && result.line_number != null ? (
              <p className="font-mono text-[11px] text-muted-foreground">Line {result.line_number}</p>
            ) : null}
            {!result.ok && result.hint ? <p>{result.hint}</p> : null}
            {!result.ok && result.line_context ? (
              <pre className="mt-1 max-h-24 overflow-auto rounded border border-border/60 bg-background/80 p-2 font-mono text-[10px] whitespace-pre-wrap">
                {result.line_context}
              </pre>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
