import { api } from "./client";
import type { Document, PaginatedResponse } from "@/lib/types/api";

export interface DocumentFilters {
  [key: string]: unknown;
  search?: string;
  contact_id?: string;
  opportunity_id?: string;
  company_id?: string;
  folder?: string;
  page?: number;
  page_size?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const documentsApi = {
  async list(filters: DocumentFilters = {}): Promise<PaginatedResponse<Document>> {
    return api.get<PaginatedResponse<Document>>("/api/documents", { query: filters });
  },
  async get(id: string): Promise<Document> {
    return api.get<Document>(`/api/documents/${id}`);
  },
  async upload(payload: {
    file: File;
    contact_id?: string;
    opportunity_id?: string;
    company_id?: string;
    folder?: string;
  }): Promise<Document> {
    const form = new FormData();
    form.append("file", payload.file);
    if (payload.contact_id) form.append("contact_id", payload.contact_id);
    if (payload.opportunity_id) form.append("opportunity_id", payload.opportunity_id);
    if (payload.company_id) form.append("company_id", payload.company_id);
    if (payload.folder) form.append("folder", payload.folder);
    const res = await fetch(`${API_BASE}/api/documents`, {
      method: "POST",
      body: form,
      credentials: "include",
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(text || `Error ${res.status}`);
    }
    return res.json() as Promise<Document>;
  },
  async remove(id: string): Promise<void> {
    return api.delete<void>(`/api/documents/${id}`);
  },
  async downloadUrl(id: string): Promise<string> {
    return `${API_BASE}/api/documents/${id}/download`;
  },
};
