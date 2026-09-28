import { api } from "./client";
import type {
  Task,
  TaskCreate,
  TaskFilters,
  PaginatedResponse,
} from "@/lib/types/api";

export const tasksApi = {
  async list(filters: TaskFilters = {}): Promise<PaginatedResponse<Task>> {
    return api.get<PaginatedResponse<Task>>("/api/tasks", { query: filters });
  },
  async get(id: string): Promise<Task> {
    return api.get<Task>(`/api/tasks/${id}`);
  },
  async create(payload: TaskCreate): Promise<Task> {
    return api.post<Task>("/api/tasks", payload);
  },
  async update(id: string, payload: Partial<TaskCreate> & { status?: Task["status"] }): Promise<Task> {
    return api.patch<Task>(`/api/tasks/${id}`, payload);
  },
  async complete(id: string): Promise<Task> {
    return api.patch<Task>(`/api/tasks/${id}`, { status: "completed" });
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/tasks/${id}`);
  },
};
