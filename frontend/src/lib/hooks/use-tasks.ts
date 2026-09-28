"use client";

import { useCallback, useEffect, useState } from "react";
import { tasksApi } from "@/lib/api/tasks";
import type { Task, TaskCreate, TaskFilters } from "@/lib/types/api";
import { toast } from "./use-toast";

export function useTasks(filters: TaskFilters) {
  const [items, setItems] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await tasksApi.list(filters);
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [
    filters.search,
    filters.status,
    filters.priority,
    filters.owner_id,
    filters.due_before,
    filters.due_after,
    filters.view,
    filters.page,
    filters.page_size,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (payload: TaskCreate) => {
      const t = await tasksApi.create(payload);
      toast.success("Tarea creada");
      await load();
      return t;
    },
    [load]
  );

  const update = useCallback(
    async (id: string, payload: Partial<TaskCreate> & { status?: Task["status"] }) => {
      const t = await tasksApi.update(id, payload);
      setItems((prev) => prev.map((x) => (x.id === id ? t : x)));
      toast.success("Tarea actualizada");
      return t;
    },
    []
  );

  const complete = useCallback(async (id: string) => {
    const t = await tasksApi.complete(id);
    setItems((prev) => prev.map((x) => (x.id === id ? t : x)));
    toast.success("Tarea completada");
    return t;
  }, []);

  const remove = useCallback(async (id: string) => {
    await tasksApi.remove(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
    setTotal((t) => Math.max(0, t - 1));
    toast.success("Tarea eliminada");
  }, []);

  return { items, total, loading, error, refresh: load, create, update, complete, remove };
}
