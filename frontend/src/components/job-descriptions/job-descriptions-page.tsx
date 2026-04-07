"use client";

import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function JobDescriptionsPage() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
      <header className="shrink-0 border-b border-border/80 bg-card/40 px-4 py-3 backdrop-blur-sm md:px-5">
        <h1 className="text-base font-semibold tracking-tight text-foreground md:text-lg">Job postings</h1>
        <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
          Job text is saved per chat so tailoring stays with the conversation.
        </p>
      </header>

      <div className="p-4 md:p-5">
        <Card className="border-border/90 bg-card/80 shadow-sm backdrop-blur-sm">
          <CardHeader className="flex flex-col gap-1 border-b border-border/60 bg-muted/15">
            <CardTitle className="text-base font-semibold tracking-tight">Add jobs in Chat</CardTitle>
            <CardDescription className="text-sm leading-relaxed">
              Go to{" "}
              <Link href="/" className="font-medium text-primary underline underline-offset-4">
                Chat
              </Link>
              , choose a session, then open the <strong>Job description</strong> section. Paste the posting and
              set it as active for PDFs.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-4 text-sm leading-relaxed text-muted-foreground">
            Tip: create or pick a chat in the sidebar first, then return here if you need this reminder.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
