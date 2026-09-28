"use client";

import { useCallback, useEffect, useState } from "react";
import { documentsApi, type DocumentFilters } from "@/lib/api/documents";
import type { Document } from "@/lib/types/api";
import { toast } from "./use-toast";

export function useDocuments(filters: DocumentFilters = {}) {
  const [items, setItems] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await documentsApi.list(filters);
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [
    filters.search,
    filters.contact_id,
    filters.opportunity_id,
    filters.company_id,
    filters.folder,
    filters.page,
    filters.page_size,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  const upload = useCallback(
    async (payload: {
      file: File;
      contact_id?: string;
      opportunity_id?: string;
      company_id?: string;
      folder?: string;
    }) => {
      const d = await documentsApi.upload(payload);
      await load();
      toast.success("Documento subido");
      return d;
    },
    [load]
  );

  const remove = useCallback(
    async (id: string) => {
      await documentsApi.remove(id);
      await load();
      toast.success("Documento eliminado");
    },
    [load]
  );

  return { items, total, loading, error, refresh: load, upload, remove };
}
