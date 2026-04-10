import type { ReactNode } from "react";

export function AppPageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description: ReactNode;
  children?: ReactNode;
}) {
  return (
    <header className="shrink-0 border-b border-border/80 bg-card/40 px-4 py-3 backdrop-blur-sm md:px-5">
      <div className="flex flex-col gap-2">
        <div className="flex min-h-8 flex-col gap-0.5">
          <h1 className="text-base font-semibold tracking-tight text-foreground md:text-lg">{title}</h1>
          <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">{description}</p>
        </div>
        {children}
      </div>
    </header>
  );
}
