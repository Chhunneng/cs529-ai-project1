export default function DashboardPage() {
  // Keep /dashboard as a simple landing page (chat).
  // Next.js redirects are server-only; we do a minimal client redirect here.
  if (typeof window !== "undefined") {
    window.location.replace("/dashboard/chat");
  }
  return null;
}

