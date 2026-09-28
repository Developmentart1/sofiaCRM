import { api } from "./client";
import type {
  Activity,
  ActivityCreate,
  PaginatedResponse,
} from "@/lib/types/api";

export interface ActivityFilters {
  [key: string]: unknown;
  type?: string;
  contact_id?: string;
  opportunity_id?: string;
  company_id?: string;
  user_id?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}

export const activitiesApi = {
  async list(filters: ActivityFilters = {}): Promise<PaginatedResponse<Activity>> {
    return api.get<PaginatedResponse<Activity>>("/api/activities", { query: filters });
  },
  async create(payload: ActivityCreate): Promise<Activity> {
    return api.post<Activity>("/api/activities", payload);
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/activities/${id}`);
  },
};
