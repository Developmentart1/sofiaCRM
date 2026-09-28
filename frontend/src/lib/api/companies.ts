import { api } from "./client";
import type {
  Company,
  CompanyCreate,
  PaginatedResponse,
} from "@/lib/types/api";

export interface CompanyFilters {
  [key: string]: unknown;
  search?: string;
  industry?: string;
  page?: number;
  page_size?: number;
  sort_by?: "name" | "created_at" | "revenue";
  sort_dir?: "asc" | "desc";
}

export const companiesApi = {
  async list(filters: CompanyFilters = {}): Promise<PaginatedResponse<Company>> {
    return api.get<PaginatedResponse<Company>>("/api/companies", { query: filters });
  },
  async get(id: string): Promise<Company> {
    return api.get<Company>(`/api/companies/${id}`);
  },
  async create(payload: CompanyCreate): Promise<Company> {
    return api.post<Company>("/api/companies", payload);
  },
  async update(id: string, payload: Partial<CompanyCreate>): Promise<Company> {
    return api.patch<Company>(`/api/companies/${id}`, payload);
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/companies/${id}`);
  },
  async contacts(id: string): Promise<unknown[]> {
    return api.get<unknown[]>(`/api/companies/${id}/contacts`);
  },
};
