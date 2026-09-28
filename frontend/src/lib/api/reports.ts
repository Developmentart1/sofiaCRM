import { api } from "./client";
import type {
  DashboardKPIs,
  ReportSummary,
  UserPerformance,
  Activity,
  Task,
  Opportunity,
  AutomationRule,
} from "@/lib/types/api";

export const reportsApi = {
  async kpis(): Promise<DashboardKPIs> {
    return api.get<DashboardKPIs>("/api/reports/kpis");
  },
  async summary(params: { from?: string; to?: string; pipeline_id?: string }): Promise<ReportSummary> {
    return api.get<ReportSummary>("/api/reports/summary", { query: params });
  },
  async performanceByUser(params: { from?: string; to?: string }): Promise<UserPerformance[]> {
    return api.get<UserPerformance[]>("/api/reports/performance", { query: params });
  },
  async recentActivity(limit = 10): Promise<Activity[]> {
    return api.get<Activity[]>("/api/activities/recent", { query: { limit } });
  },
  async upcomingTasks(limit = 10): Promise<Task[]> {
    return api.get<Task[]>("/api/tasks/upcoming", { query: { limit } });
  },
  async stuckOpportunities(): Promise<Opportunity[]> {
    return api.get<Opportunity[]>("/api/opportunities/stuck");
  },
  async getPipelineTrend(params: { days?: number }): Promise<Array<{ date: string; value: number }>> {
    return api.get<Array<{ date: string; value: number }>>("/api/reports/pipeline/trend", { query: params });
  },
  async getPipelineStageDistribution(): Promise<Array<{ stage_name: string; count: number }>> {
    return api.get<Array<{ stage_name: string; count: number }>>("/api/reports/pipeline/distribution");
  },
};

export const automationsApi = {
  async list(): Promise<AutomationRule[]> {
    return api.get<AutomationRule[]>("/api/automations");
  },
  async get(id: string): Promise<AutomationRule> {
    return api.get<AutomationRule>(`/api/automations/${id}`);
  },
  async create(payload: Omit<AutomationRule, "id" | "created_at" | "updated_at">): Promise<AutomationRule> {
    return api.post<AutomationRule>("/api/automations", payload);
  },
  async update(id: string, payload: Partial<AutomationRule>): Promise<AutomationRule> {
    return api.patch<AutomationRule>(`/api/automations/${id}`, payload);
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/automations/${id}`);
  },
  async toggle(id: string, is_active: boolean): Promise<AutomationRule> {
    return api.patch<AutomationRule>(`/api/automations/${id}`, { is_active });
  },
};
