import { AppPageHeader } from "@/components/layout/app-page-header";
import { OutputsPage } from "@/components/outputs/outputs-page";

const OUTPUTS_PAGE_DESCRIPTION =
  "Build an ATS-oriented resume PDF by choosing a template, your resume, and a saved job description. No chat session is required.";

export default function OutputsRoutePage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <AppPageHeader title="PDF exports" description={OUTPUTS_PAGE_DESCRIPTION} />
      <OutputsPage />
    </div>
  );
}
