"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard/chat", label: "Chat" },
  { href: "/dashboard/resumes", label: "Resumes" },
  { href: "/dashboard/job-descriptions", label: "Job Descriptions" },
  { href: "/dashboard/templates", label: "Templates" },
  { href: "/dashboard/outputs", label: "Outputs" },
] as const;

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex h-dvh w-full bg-background">
      <aside className="hidden w-64 shrink-0 border-r border-border/80 bg-card/40 p-4 backdrop-blur-sm md:flex md:flex-col">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-sm font-semibold tracking-tight">
            AI Resume Agent
          </Link>
        </div>

        <nav className="mt-6 flex flex-col gap-1">
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}

