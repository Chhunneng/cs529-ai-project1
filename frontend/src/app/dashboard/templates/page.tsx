"use client";

import { useEffect, useMemo, useState } from "react";

import { pingBackend, type ResumeTemplateListItem } from "@/lib/api";
import { TemplateEditor } from "@/components/templates/template-editor";
import { useTemplates } from "@/components/templates/use-templates";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const NONE = "__none__";

function defaultSchema(): Record<string, unknown> {
  return {
    type: "object",
    properties: {},
  };
}

function listLabel(t: ResumeTemplateListItem) {
  return `${t.name} (${t.id})`;
}

export default function DashboardTemplatesPage() {
  const [connection, setConnection] = useState<"checking" | "ready" | "offline">("checking");
  const apiReady = connection === "ready";

  useEffect(() => {
    let cancelled = false;
    pingBackend().then((ok) => {
      if (!cancelled) setConnection(ok ? "ready" : "offline");
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const { items, active, loadDetail, create, save, loadingList, loadingDetail, error } = useTemplates(apiReady);

  const [picker, setPicker] = useState(NONE);

  useEffect(() => {
    if (picker === NONE) return;
    void loadDetail(picker);
  }, [picker, loadDetail]);

  useEffect(() => {
    if (active?.id) setPicker(active.id);
  }, [active?.id]);

  const [createOpen, setCreateOpen] = useState(false);
  const [newId, setNewId] = useState("custom-v1");
  const [newName, setNewName] = useState("Custom Template");
  const [newLatex, setNewLatex] = useState("");
  const [newSchemaText, setNewSchemaText] = useState(JSON.stringify(defaultSchema(), null, 2));
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const parsedNewSchema = useMemo(() => {
    try {
      const v = JSON.parse(newSchemaText) as unknown;
      if (!v || typeof v !== "object" || Array.isArray(v)) return null;
      return v as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [newSchemaText]);

  async function handleCreate() {
    setCreateError(null);
    if (!parsedNewSchema) {
      setCreateError("Schema JSON is invalid.");
      return;
    }
    if (!newId.trim() || !newName.trim() || !newLatex.trim()) {
      setCreateError("ID, name, and LaTeX are required.");
      return;
    }
    setCreating(true);
    try {
      await create({
        id: newId.trim(),
        name: newName.trim(),
        latex_source: newLatex,
        schema_json: parsedNewSchema,
      });
      setCreateOpen(false);
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "Create failed.");
    } finally {
      setCreating(false);
    }
  }

  async function handleSave(args: {
    id: string;
    name: string;
    latex_source: string;
    schema_json: Record<string, unknown>;
  }) {
    await save(args.id, { name: args.name, latex_source: args.latex_source, schema_json: args.schema_json });
  }

  return (
    <div className="flex h-full w-full flex-col gap-5 p-4 md:p-5">
      {connection === "offline" ? (
        <Alert variant="destructive" className="border-destructive/50">
          <AlertTitle>Backend unreachable</AlertTitle>
          <AlertDescription>Check NEXT_PUBLIC_API_BASE_URL and that the API is running.</AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive" className="border-destructive/50">
          <AlertTitle>Templates error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-5 lg:grid-cols-[360px_1fr]">
        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="space-y-1 border-b border-border/60 bg-muted/15">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-base font-semibold tracking-tight">Templates</CardTitle>
                <CardDescription className="text-sm leading-relaxed">
                  Create and edit LaTeX templates used for resume rendering.
                </CardDescription>
              </div>
              <Button size="sm" variant="outline" disabled={!apiReady} onClick={() => setCreateOpen(true)}>
                New
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-col gap-3 p-4">
            {loadingList ? <Skeleton className="h-8 w-full" /> : null}
            {items.length === 0 && !loadingList ? (
              <Empty className="min-h-[180px] border-none bg-muted/15 py-8">
                <EmptyHeader>
                  <EmptyTitle className="font-semibold tracking-tight">No templates</EmptyTitle>
                  <EmptyDescription>Create one to start rendering.</EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <>
                <Select value={picker} onValueChange={(v) => setPicker(v ?? NONE)}>
                  <SelectTrigger className="w-full" size="sm">
                    <SelectValue placeholder="Select a template" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>None</SelectItem>
                    {items.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <div className="flex flex-col gap-2">
                  {items.slice(0, 8).map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setPicker(t.id)}
                      className="flex w-full items-center justify-between gap-3 rounded-lg border border-border/70 bg-muted/10 px-3 py-2 text-left text-sm hover:bg-muted/20"
                    >
                      <span className="truncate">{listLabel(t)}</span>
                      <Badge variant={picker === t.id ? "default" : "secondary"}>{picker === t.id ? "active" : "—"}</Badge>
                    </button>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <TemplateEditor template={active} loading={loadingDetail} onSave={handleSave} />
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create template</DialogTitle>
            <DialogDescription>Provide an id, name, LaTeX source, and schema JSON.</DialogDescription>
          </DialogHeader>
          {createError ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Create failed</AlertTitle>
              <AlertDescription>{createError}</AlertDescription>
            </Alert>
          ) : null}
          <div className="flex flex-col gap-3">
            <Input value={newId} onChange={(e) => setNewId(e.target.value)} placeholder="custom-v1" />
            <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Custom Template" />
            <textarea
              value={newLatex}
              onChange={(e) => setNewLatex(e.target.value)}
              className="min-h-[160px] w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring/25"
              placeholder="Paste LaTeX here…"
            />
            <textarea
              value={newSchemaText}
              onChange={(e) => setNewSchemaText(e.target.value)}
              className="min-h-[160px] w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring/25"
            />
          </div>
          <DialogFooter className="flex flex-row gap-2 sm:justify-end">
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!apiReady || creating || !parsedNewSchema} onClick={() => void handleCreate()}>
              {creating ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

