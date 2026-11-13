import { api } from "./client";
import type {
  Contact,
  ContactCreate,
  ContactFilters,
  Activity,
  Task,
  Opportunity,
  Document,
  AuditLog,
} from "@/lib/types/api";

export const contactsApi = {
  async list(filters: ContactFilters = {}): Promise<Contact[]> {
    return api.get<Contact[]>("/api/contacts", { query: filters });
  },
  async get(id: string): Promise<Contact> {
    return api.get<Contact>(`/api/contacts/${id}`);
  },
  async create(payload: ContactCreate): Promise<Contact> {
    return api.post<Contact>("/api/contacts", payload);
  },
  async update(id: string, payload: Partial<ContactCreate>): Promise<Contact> {
    return api.patch<Contact>(`/api/contacts/${id}`, payload);
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/contacts/${id}`);
  },
  async activities(id: string): Promise<Activity[]> {
    return api.get<Activity[]>(`/api/contacts/${id}/activities`);
  },
  async tasks(id: string): Promise<Task[]> {
    return api.get<Task[]>(`/api/contacts/${id}/tasks`);
  },
  async opportunities(id: string): Promise<Opportunity[]> {
    return api.get<Opportunity[]>(`/api/contacts/${id}/opportunities`);
  },
  async documents(id: string): Promise<Document[]> {
    return api.get<Document[]>(`/api/contacts/${id}/documents`);
  },
  async audit(id: string): Promise<AuditLog[]> {
    return api.get<AuditLog[]>(`/api/contacts/${id}/audit`);
  },
  async checkDuplicates(payload: { email?: string; phone?: string }): Promise<Contact[]> {
    return api.get<Contact[]>("/api/contacts/duplicates", { query: payload });
  },
  async importCsv(file: File): Promise<{ created: number; updated: number; errors: Array<{ row: number; error: string }> }> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/contacts/import`,
      { method: "POST", body: form, credentials: "include" }
    );
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `Error ${res.status}`);
    }
    return res.json();
  },
};
