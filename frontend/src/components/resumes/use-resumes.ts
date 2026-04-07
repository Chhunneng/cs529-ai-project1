"use client";

import { useCallback, useEffect, useState } from "react";

import { createResume, listResumes, type ResumeListItem } from "@/lib/api";

export function useResumes(apiReady: boolean) {
  const [items, setItems] = useState<ResumeListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!apiReady) return;
    setError(null);
    setLoading(true);
    try {
      const rows = await listResumes();
      setItems(rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load resumes.");
    } finally {
      setLoading(false);
    }
  }, [apiReady]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const createStub = useCallback(
    async (filename: string) => {
      if (!apiReady) throw new Error("API unavailable");
      setError(null);
      await createResume(filename);
      await refresh();
    },
    [apiReady, refresh],
  );

  return { items, loading, error, refresh, createStub };
}

