"use client";

import { useCallback, useEffect, useState } from "react";
import { contactsApi } from "@/lib/api/contacts";
import { companiesApi } from "@/lib/api/companies";
import type {
  Contact,
  ContactCreate,
  ContactFilters,
  Company,
  CompanyCreate,
  CompanyFilters,
  Activity,
  Task,
  Opportunity,
  Document,
  AuditLog,
} from "@/lib/types/api";
import { toast } from "./use-toast";

export function useContacts(filters: ContactFilters) {
  const [items, setItems] = useState<Contact[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await contactsApi.list(filters);
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
    filters.company_id,
    filters.owner_id,
    filters.tag,
    filters.page,
    filters.page_size,
    filters.sort_by,
    filters.sort_dir,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(async (payload: ContactCreate) => {
    const c = await contactsApi.create(payload);
    toast.success("Contacto creado");
    await load();
    return c;
  }, [load]);

  const update = useCallback(async (id: string, payload: Partial<ContactCreate>) => {
    const c = await contactsApi.update(id, payload);
    setItems((prev) => prev.map((x) => (x.id === id ? c : x)));
    toast.success("Contacto actualizado");
    return c;
  }, []);

  const remove = useCallback(async (id: string) => {
    await contactsApi.remove(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
    setTotal((t) => Math.max(0, t - 1));
    toast.success("Contacto eliminado");
  }, []);

  return { items, total, loading, error, refresh: load, create, update, remove };
}

export function useContact(id: string | undefined) {
  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const c = await contactsApi.get(id);
      setContact(c);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  return { contact, loading, error, refresh: load, setContact };
}

export function useContactActivities(id: string | undefined) {
  const [items, setItems] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      setItems(await contactsApi.activities(id));
    } finally {
      setLoading(false);
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  return { items, loading, refresh: load };
}

export function useContactTasks(id: string | undefined) {
  const [items, setItems] = useState<Task[]>([]);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      setItems(await contactsApi.tasks(id));
    } finally {
      setLoading(false);
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  return { items, loading, refresh: load };
}

export function useContactOpportunities(id: string | undefined) {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      setItems(await contactsApi.opportunities(id));
    } finally {
      setLoading(false);
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  return { items, loading, refresh: load };
}

export function useContactDocuments(id: string | undefined) {
  const [items, setItems] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      setItems(await contactsApi.documents(id));
    } finally {
      setLoading(false);
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  return { items, loading, refresh: load };
}

export function useContactAudit(id: string | undefined) {
  const [items, setItems] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      setItems(await contactsApi.audit(id));
    } finally {
      setLoading(false);
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  return { items, loading, refresh: load };
}

export function useCompanies(filters: CompanyFilters) {
  const [items, setItems] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await companiesApi.list(filters);
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [
    filters.search,
    filters.industry,
    filters.page,
    filters.page_size,
    filters.sort_by,
    filters.sort_dir,
  ]);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(async (payload: CompanyCreate) => {
    const c = await companiesApi.create(payload);
    toast.success("Empresa creada");
    await load();
    return c;
  }, [load]);

  const update = useCallback(async (id: string, payload: Partial<CompanyCreate>) => {
    const c = await companiesApi.update(id, payload);
    setItems((prev) => prev.map((x) => (x.id === id ? c : x)));
    toast.success("Empresa actualizada");
    return c;
  }, []);

  const remove = useCallback(async (id: string) => {
    await companiesApi.remove(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
    setTotal((t) => Math.max(0, t - 1));
    toast.success("Empresa eliminada");
  }, []);

  return { items, total, loading, error, refresh: load, create, update, remove };
}

export function useCompany(id: string | undefined) {
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      setCompany(await companiesApi.get(id));
    } finally {
      setLoading(false);
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  return { company, loading, refresh: load, setCompany };
}
