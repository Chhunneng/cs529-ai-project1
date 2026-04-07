"use client";

import { TemplatesManageCore } from "@/components/templates/templates-manage-core";

export function TemplatesRoutePage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <header className="shrink-0 border-b border-border/80 bg-card/40 px-4 py-3 backdrop-blur-sm md:px-5">
        <h1 className="text-base font-semibold tracking-tight text-foreground md:text-lg">Templates</h1>
        <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
          Design how exported PDFs look. The same list opens from Chat using <strong>Manage</strong> next to
          Template.
        </p>
      </header>
      <TemplatesManageCore active scrollAreaClassName="min-h-0 w-full flex-1" />
    </div>
  );
}
