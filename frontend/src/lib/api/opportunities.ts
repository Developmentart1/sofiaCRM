import { api } from "./client";
import type {
  Opportunity,
  OpportunityCreate,
  OpportunityFilters,
  PaginatedResponse,
  StageTransition,
  Activity,
  Pipeline,
  PipelineStage,
} from "@/lib/types/api";

export const opportunitiesApi = {
  async list(filters: OpportunityFilters = {}): Promise<PaginatedResponse<Opportunity>> {
    return api.get<PaginatedResponse<Opportunity>>("/api/opportunities", { query: filters });
  },
  async get(id: string): Promise<Opportunity> {
    return api.get<Opportunity>(`/api/opportunities/${id}`);
  },
  async create(payload: OpportunityCreate): Promise<Opportunity> {
    return api.post<Opportunity>("/api/opportunities", payload);
  },
  async update(id: string, payload: Partial<OpportunityCreate> & { name?: string }): Promise<Opportunity> {
    return api.patch<Opportunity>(`/api/opportunities/${id}`, payload);
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/opportunities/${id}`);
  },
  async transition(id: string, payload: StageTransition): Promise<Opportunity> {
    return api.post<Opportunity>(`/api/opportunities/${id}/transition`, payload);
  },
  async activities(id: string): Promise<Activity[]> {
    return api.get<Activity[]>(`/api/opportunities/${id}/activities`);
  },
  async reorder(payload: { id: string; stage_id: string; position: number }): Promise<Opportunity> {
    return api.patch<Opportunity>(`/api/opportunities/${payload.id}/position`, {
      stage_id: payload.stage_id,
      position: payload.position,
    });
  },
};

export const pipelinesApi = {
  async list(): Promise<Pipeline[]> {
    return api.get<Pipeline[]>("/api/pipelines");
  },
  async get(id: string): Promise<Pipeline & { stages: PipelineStage[] }> {
    return api.get<Pipeline & { stages: PipelineStage[] }>(`/api/pipelines/${id}`);
  },
  async create(payload: { name: string; description?: string; is_default?: boolean }): Promise<Pipeline> {
    return api.post<Pipeline>("/api/pipelines", payload);
  },
  async update(id: string, payload: { name?: string; description?: string; is_default?: boolean }): Promise<Pipeline> {
    return api.patch<Pipeline>(`/api/pipelines/${id}`, payload);
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/pipelines/${id}`);
  },
  async stages(pipelineId: string): Promise<PipelineStage[]> {
    return api.get<PipelineStage[]>(`/api/pipelines/${pipelineId}/stages`);
  },
  async createStage(pipelineId: string, payload: Omit<PipelineStage, "id" | "pipeline_id">): Promise<PipelineStage> {
    return api.post<PipelineStage>(`/api/pipelines/${pipelineId}/stages`, payload);
  },
  async updateStage(stageId: string, payload: Partial<Omit<PipelineStage, "id" | "pipeline_id">>): Promise<PipelineStage> {
    return api.patch<PipelineStage>(`/api/pipelines/stages/${stageId}`, payload);
  },
  async removeStage(stageId: string): Promise<void> {
    return api.delete<void>(`/api/pipelines/stages/${stageId}`);
  },
  async reorderStages(pipelineId: string, orderedIds: string[]): Promise<PipelineStage[]> {
    return api.patch<PipelineStage[]>(`/api/pipelines/${pipelineId}/stages/reorder`, {
      ordered_ids: orderedIds,
    });
  },
};
