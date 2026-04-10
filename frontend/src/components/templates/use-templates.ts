"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createResumeTemplate,
  deleteResumeTemplate,
  getResumeTemplate,
  listResumeTemplates,
  patchResumeTemplate,
  type ResumeTemplateDetail,
  type ResumeTemplateListItem,
} from "@/lib/api";

export function useTemplates(apiReady: boolean) {
  const [items, setItems] = useState<ResumeTemplateListItem[]>([]);
  const [active, setActive] = useState<ResumeTemplateDetail | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshList = useCallback(async () => {
    if (!apiReady) return;
    setError(null);
    setLoadingList(true);
    try {
      const pageSize = 200;
      let offset = 0;
      const all: ResumeTemplateListItem[] = [];
      let total = 0;
      for (;;) {
        const page = await listResumeTemplates({ limit: pageSize, offset });
        all.push(...page.items);
        total = page.total;
        offset += page.items.length;
        if (page.items.length === 0 || all.length >= total) break;
      }
      setItems(all);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load templates.");
    } finally {
      setLoadingList(false);
    }
  }, [apiReady]);

  useEffect(() => {
    void refreshList();
  }, [refreshList]);

  const loadDetail = useCallback(
    async (id: string) => {
      if (!apiReady) return;
      setError(null);
      setLoadingDetail(true);
      try {
        const tpl = await getResumeTemplate(id);
        setActive(tpl);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load template.");
      } finally {
        setLoadingDetail(false);
      }
    },
    [apiReady],
  );

  const create = useCallback(
    async (body: { name: string; latex_source: string }) => {
      if (!apiReady) throw new Error("API unavailable");
      setError(null);
      const tpl = await createResumeTemplate({
        name: body.name,
        latex_source: body.latex_source,
      });
      await refreshList();
      setActive(tpl);
      return tpl;
    },
    [apiReady, refreshList],
  );

  const save = useCallback(
    async (id: string, body: { name: string; latex_source: string }) => {
      if (!apiReady) throw new Error("API unavailable");
      setError(null);
      const tpl = await patchResumeTemplate(id, {
        name: body.name,
        latex_source: body.latex_source,
      });
      await refreshList();
      setActive(tpl);
      return tpl;
    },
    [apiReady, refreshList],
  );

  const remove = useCallback(
    async (id: string) => {
      if (!apiReady) throw new Error("API unavailable");
      setError(null);
      await deleteResumeTemplate(id);
      await refreshList();
      setActive(null);
    },
    [apiReady, refreshList],
  );

  return {
    items,
    active,
    setActive,
    refreshList,
    loadDetail,
    create,
    save,
    remove,
    loadingList,
    loadingDetail,
    error,
  };
}

