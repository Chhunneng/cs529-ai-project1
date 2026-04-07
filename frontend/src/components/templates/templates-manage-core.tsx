"use client";

import { useEffect, useMemo, useState } from "react";

import { pingBackend } from "@/lib/api";
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
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Trash2 } from "lucide-react";

const NONE = "__none__";

function defaultSchema(): Record<string, unknown> {
  return {
    type: "object",
    properties: {},
  };
}

export function TemplatesManageCore({
  active,
  onTemplatesChanged,
  scrollAreaClassName,
}: {
  active: boolean;
  onTemplatesChanged?: () => void;
  scrollAreaClassName?: string;
}) {
  const [connection, setConnection] = useState<"checking" | "ready" | "offline">("checking");
  const apiReady = connection === "ready";

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    pingBackend().then((ok) => {
      if (!cancelled) setConnection(ok ? "ready" : "offline");
    });
    return () => {
      cancelled = true;
    };
  }, [active]);

  const {
    items,
    active: activeTpl,
    loadDetail,
    create,
    save,
    remove,
    loadingList,
    loadingDetail,
    error,
  } = useTemplates(apiReady && active);

  const [picker, setPicker] = useState(NONE);

  useEffect(() => {
    if (!active) return;
    if (picker === NONE) return;
    void loadDetail(picker);
  }, [active, picker, loadDetail]);

  useEffect(() => {
    if (activeTpl?.id) setPicker(activeTpl.id);
  }, [activeTpl?.id]);

  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState("Custom Template");
  const [newLatex, setNewLatex] = useState("");
  const [newSchemaText, setNewSchemaText] = useState(JSON.stringify(defaultSchema(), null, 2));
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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
    if (!newName.trim() || !newLatex.trim()) {
      setCreateError("Name and LaTeX are required.");
      return;
    }
    setCreating(true);
    try {
      const tpl = await create({
        name: newName.trim(),
        latex_source: newLatex,
        schema_json: parsedNewSchema,
      });
      setCreateOpen(false);
      setPicker(tpl.id);
      onTemplatesChanged?.();
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
    onTemplatesChanged?.();
  }

  async function confirmDeleteTemplate() {
    if (!pendingDeleteId) return;
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await remove(pendingDeleteId);
      setPendingDeleteId(null);
      setPicker(NONE);
      onTemplatesChanged?.();
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : "Could not delete template.");
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      <ScrollArea className={scrollAreaClassName ?? "min-h-0 w-full flex-1"}>
        <div className="flex flex-col gap-4 p-4 lg:min-h-[min(70vh,640px)] lg:flex-row lg:gap-4">
          {connection === "offline" ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Backend unreachable</AlertTitle>
              <AlertDescription>
                Check NEXT_PUBLIC_API_BASE_URL and that the API is running.
              </AlertDescription>
            </Alert>
          ) : null}

          {error ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Templates error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <Card className="flex min-h-0 shrink-0 flex-col border-border/90 bg-card/80 shadow-sm backdrop-blur-sm lg:w-[min(100%,360px)]">
            <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15">
              <div className="flex flex-row flex-wrap items-start justify-between gap-3">
                <div className="flex flex-col gap-1">
                  <CardTitle className="text-base font-semibold tracking-tight">Library</CardTitle>
                  <CardDescription className="text-sm leading-relaxed">
                    Pick a template to edit.
                  </CardDescription>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!apiReady}
                  type="button"
                  onClick={() => setCreateOpen(true)}
                >
                  New
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex min-h-0 flex-1 flex-col gap-3 p-4">
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

                  <div className="flex max-h-[240px] flex-col gap-2 overflow-y-auto lg:max-h-none">
                    {items.slice(0, 12).map((t) => {
                      const isActive = picker === t.id;
                      return (
                        <div
                          key={t.id}
                          role="row"
                          className="flex min-h-11 w-full shrink-0 items-center gap-2 rounded-lg border border-border/70 bg-muted/10 px-2 py-1.5 pl-3 text-left text-sm hover:bg-muted/20"
                        >
                          <button
                            type="button"
                            onClick={() => setPicker(t.id)}
                            className="flex min-h-0 min-w-0 flex-1 flex-col items-stretch justify-center gap-0.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25 rounded-sm -my-0.5 py-1"
                          >
                            <span className="truncate font-medium leading-tight text-foreground">{t.name}</span>
                            <span className="truncate font-mono text-[10px] leading-tight text-muted-foreground">
                              {t.id.slice(0, 8)}…{t.id.slice(-4)}
                            </span>
                          </button>
                          <Badge
                            variant={isActive ? "default" : "secondary"}
                            className="shrink-0 self-center whitespace-nowrap text-[10px] uppercase tracking-wide"
                          >
                            {isActive ? "Active" : "—"}
                          </Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="size-8 shrink-0 text-muted-foreground hover:text-destructive"
                            disabled={!apiReady || loadingList}
                            aria-label={`Delete template ${t.name}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteError(null);
                              setPendingDeleteId(t.id);
                            }}
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <div className="min-h-[280px] min-w-0 flex-1 lg:min-h-0">
            <TemplateEditor template={activeTpl} loading={loadingDetail} onSave={handleSave} />
          </div>
        </div>
      </ScrollArea>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create template</DialogTitle>
            <DialogDescription>Provide a name, LaTeX source, and schema JSON. The server assigns a template id.</DialogDescription>
          </DialogHeader>
          {createError ? (
            <Alert variant="destructive" className="border-destructive/50">
              <AlertTitle>Create failed</AlertTitle>
              <AlertDescription>{createError}</AlertDescription>
            </Alert>
          ) : null}
          <div className="flex flex-col gap-3">
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

      <Dialog
        open={pendingDeleteId != null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDeleteId(null);
            setDeleteError(null);
          }
        }}
      >
        <DialogContent showCloseButton className="gap-0 sm:max-w-md">
          <DialogHeader className="space-y-2 pr-8 text-left">
            <DialogTitle className="leading-snug">Delete this template?</DialogTitle>
            <DialogDescription>
              This permanently removes the template from the database. Existing resume outputs are kept; their link to
              this template is cleared.
            </DialogDescription>
          </DialogHeader>
          {deleteError ? (
            <p className="mt-3 text-sm leading-relaxed text-destructive">{deleteError}</p>
          ) : null}
          <div className="mt-4 flex flex-col-reverse gap-2 border-t border-border/70 pt-3 sm:flex-row sm:justify-end sm:gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={isDeleting}
              className="w-full sm:w-auto"
              onClick={() => {
                setPendingDeleteId(null);
                setDeleteError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={isDeleting}
              className="w-full font-medium sm:w-auto"
              onClick={() => void confirmDeleteTemplate()}
            >
              {isDeleting ? "Deleting…" : "Delete template"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
