"use client";

import { AppPageHeader } from "@/components/layout/app-page-header";
import { TemplatesManageCore } from "@/components/templates/templates-manage-core";

export function TemplatesRoutePage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <AppPageHeader
        title="Templates"
        description={
          <>
            Design how exported PDFs look. The same list opens from Chat using <strong>Manage</strong> next to
            Template.
          </>
        }
      />
      <TemplatesManageCore active scrollAreaClassName="min-h-0 w-full flex-1" />
    </div>
  );
}
