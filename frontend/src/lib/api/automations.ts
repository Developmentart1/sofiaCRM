import { api } from "./client";
import type {
  AutomationRuleRead,
  AutomationRuleCreate,
  AutomationExecution,
  AutomationTestResult,
  PaginatedResponse,
} from "@/lib/types/api";

export interface AutomationExecutionFilters {
  [key: string]: unknown;
  rule_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export const automationsApi = {
  async listRules(): Promise<AutomationRuleRead[]> {
    return api.get<AutomationRuleRead[]>("/api/automations/rules");
  },
  async getRule(id: string): Promise<AutomationRuleRead> {
    return api.get<AutomationRuleRead>(`/api/automations/rules/${id}`);
  },
  async createRule(payload: AutomationRuleCreate): Promise<AutomationRuleRead> {
    return api.post<AutomationRuleRead>("/api/automations/rules", payload);
  },
  async updateRule(id: string, payload: Partial<AutomationRuleCreate>): Promise<AutomationRuleRead> {
    return api.patch<AutomationRuleRead>(`/api/automations/rules/${id}`, payload);
  },
  async toggleRule(id: string, is_active: boolean): Promise<AutomationRuleRead> {
    return api.patch<AutomationRuleRead>(`/api/automations/rules/${id}`, { is_active });
  },
  async removeRule(id: string): Promise<void> {
    return api.delete<void>(`/api/automations/rules/${id}`);
  },
  async listExecutions(filters: AutomationExecutionFilters = {}): Promise<PaginatedResponse<AutomationExecution>> {
    return api.get<PaginatedResponse<AutomationExecution>>("/api/automations/executions", { query: filters });
  },
  async testRule(id: string, payload: { event_type: string; payload: Record<string, unknown> }): Promise<AutomationTestResult> {
    return api.post<AutomationTestResult>(`/api/automations/rules/${id}/test`, payload);
  },
};
