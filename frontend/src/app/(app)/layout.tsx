"use client";

import { AppShell } from "@/components/chat/app-shell";
import { ChatWorkspaceProvider } from "@/components/chat/use-chat-workspace";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChatWorkspaceProvider>
      <AppShell>{children}</AppShell>
    </ChatWorkspaceProvider>
  );
}
