import {
  Briefcase,
  FileDown,
  FileText,
  LayoutTemplate,
  MessageSquare,
  Mic,
  type LucideIcon,
} from "lucide-react";

export const SIDEBAR_NAV: readonly { href: string; label: string; icon: LucideIcon }[] = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/resumes", label: "Resumes", icon: FileText },
  { href: "/job-descriptions", label: "Jobs", icon: Briefcase },
  { href: "/interview-practice", label: "Interview", icon: Mic },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/outputs", label: "PDF exports", icon: FileDown },
];

export function navActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
