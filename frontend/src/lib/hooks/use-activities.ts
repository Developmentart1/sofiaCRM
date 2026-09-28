"use client";

import { useCallback, useEffect, useState } from "react";
import { activitiesApi, type ActivityFilters } from "@/lib/api/activities";
import type { Activity, ActivityCreate } from "@/lib/types/api";
import { toast } from "./use-toast";

export function useActivities(filters: ActivityFilters = {}) {
  const [items, setItems] = useState<Activity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await activitiesApi.list(filters);
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [
    filters.type,
    filters.contact_id,
    filters.opportunity_id,
    filters.company_id,
    filters.user_id,
    filters.from,
    filters.to,
    filters.page,
    filters.page_size,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (payload: ActivityCreate) => {
      const a = await activitiesApi.create(payload);
      toast.success("Actividad registrada");
      await load();
      return a;
    },
    [load]
  );

  const remove = useCallback(
    async (id: string) => {
      await activitiesApi.remove(id);
      await load();
      toast.success("Actividad eliminada");
    },
    [load]
  );

  return { items, total, loading, error, refresh: load, create, remove };
}
