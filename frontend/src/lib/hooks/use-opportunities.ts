"use client";

import { useCallback, useEffect, useState } from "react";
import { opportunitiesApi, pipelinesApi } from "@/lib/api/opportunities";
import type {
  Activity,
  Opportunity,
  OpportunityCreate,
  OpportunityFilters,
  Pipeline,
  PipelineStage,
  StageTransition,
} from "@/lib/types/api";
import { toast } from "./use-toast";

export function useOpportunities(filters: OpportunityFilters) {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await opportunitiesApi.list(filters);
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
    filters.pipeline_id,
    filters.stage_id,
    filters.owner_id,
    filters.contact_id,
    filters.company_id,
    filters.min_amount,
    filters.max_amount,
    filters.page,
    filters.page_size,
    filters.sort_by,
    filters.sort_dir,
    filters.view,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(async (payload: OpportunityCreate) => {
    const c = await opportunitiesApi.create(payload);
    toast.success("Oportunidad creada");
    await load();
    return c;
  }, [load]);

  const update = useCallback(
    async (id: string, payload: Partial<OpportunityCreate> & { name?: string }) => {
      const c = await opportunitiesApi.update(id, payload);
      setItems((prev) => prev.map((x) => (x.id === id ? c : x)));
      toast.success("Oportunidad actualizada");
      return c;
    },
    []
  );

  const remove = useCallback(async (id: string) => {
    await opportunitiesApi.remove(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
    setTotal((t) => Math.max(0, t - 1));
    toast.success("Oportunidad eliminada");
  }, []);

  const transition = useCallback(async (id: string, payload: StageTransition) => {
    const c = await opportunitiesApi.transition(id, payload);
    setItems((prev) => prev.map((x) => (x.id === id ? c : x)));
    toast.success("Etapa actualizada");
    return c;
  }, []);

  const reorder = useCallback(
    async (payload: { id: string; stage_id: string; position: number }) => {
      const c = await opportunitiesApi.reorder(payload);
      setItems((prev) => prev.map((x) => (x.id === c.id ? c : x)));
      return c;
    },
    []
  );

  return { items, total, loading, error, refresh: load, create, update, remove, transition, reorder };
}

export function useOpportunity(id: string | undefined) {
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [opp, acts] = await Promise.all([
        opportunitiesApi.get(id),
        opportunitiesApi.activities(id).catch(() => []),
      ]);
      setOpportunity(opp);
      setActivities(acts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  return { opportunity, activities, loading, error, refresh: load, setOpportunity };
}

export function usePipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPipelines(await pipelinesApi.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (payload: { name: string; description?: string; is_default?: boolean }) => {
      const p = await pipelinesApi.create(payload);
      await load();
      toast.success("Pipeline creado");
      return p;
    },
    [load]
  );

  const update = useCallback(
    async (id: string, payload: { name?: string; description?: string; is_default?: boolean }) => {
      const p = await pipelinesApi.update(id, payload);
      setPipelines((prev) => prev.map((x) => (x.id === id ? p : x)));
      toast.success("Pipeline actualizado");
      return p;
    },
    []
  );

  const remove = useCallback(
    async (id: string) => {
      await pipelinesApi.remove(id);
      setPipelines((prev) => prev.filter((x) => x.id !== id));
      toast.success("Pipeline eliminado");
    },
    []
  );

  return { pipelines, loading, error, refresh: load, create, update, remove };
}

export function usePipeline(id: string | undefined) {
  const [pipeline, setPipeline] = useState<(Pipeline & { stages: PipelineStage[] }) | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setPipeline(await pipelinesApi.get(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const addStage = useCallback(
    async (payload: Omit<PipelineStage, "id" | "pipeline_id">) => {
      if (!id) throw new Error("Pipeline id missing");
      const stage = await pipelinesApi.createStage(id, payload);
      setPipeline((prev) =>
        prev ? { ...prev, stages: [...prev.stages, stage] } : prev
      );
      toast.success("Etapa creada");
      return stage;
    },
    [id]
  );

  const updateStage = useCallback(
    async (stageId: string, payload: Partial<Omit<PipelineStage, "id" | "pipeline_id">>) => {
      const stage = await pipelinesApi.updateStage(stageId, payload);
      setPipeline((prev) =>
        prev
          ? { ...prev, stages: prev.stages.map((s) => (s.id === stageId ? stage : s)) }
          : prev
      );
      toast.success("Etapa actualizada");
      return stage;
    },
    []
  );

  const removeStage = useCallback(
    async (stageId: string) => {
      await pipelinesApi.removeStage(stageId);
      setPipeline((prev) =>
        prev ? { ...prev, stages: prev.stages.filter((s) => s.id !== stageId) } : prev
      );
      toast.success("Etapa eliminada");
    },
    []
  );

  const reorderStages = useCallback(
    async (orderedIds: string[]) => {
      if (!id) throw new Error("Pipeline id missing");
      const stages = await pipelinesApi.reorderStages(id, orderedIds);
      setPipeline((prev) => (prev ? { ...prev, stages } : prev));
      toast.success("Orden actualizado");
      return stages;
    },
    [id]
  );

  return { pipeline, loading, error, refresh: load, addStage, updateStage, removeStage, reorderStages };
}
