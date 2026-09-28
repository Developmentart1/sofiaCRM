"use client";

import * as React from "react";
import { useState } from "react";
import Link from "next/link";
import { Plus, Upload, Users as UsersIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useContacts } from "@/lib/hooks/use-contacts";
import { useCompanies } from "@/lib/hooks/use-contacts";
import { useDebounce } from "@/lib/hooks/use-debounce";
import { ContactTable } from "@/components/contacts/contact-table";
import { ContactFiltersBar } from "@/components/contacts/contact-filters";
import { EmptyState } from "@/components/common/empty-state";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import type { Contact, ContactFilters } from "@/lib/types/api";

export default function ContactsPage() {
  const [filters, setFilters] = useState<ContactFilters>({ page: 1, page_size: 20, sort_by: "created_at", sort_dir: "desc" });
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);
  const [toDelete, setToDelete] = useState<Contact | null>(null);
  const [deleting, setDeleting] = useState(false);

  const { items, total, loading, remove } = useContacts({
    ...filters,
    search: debouncedSearch || undefined,
  });

  const handleDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await remove(toDelete.id);
      setToDelete(null);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Contactos</h1>
          <p className="text-sm text-muted-foreground">{total} contactos en total</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/contacts/import"><Upload className="mr-2 h-4 w-4" /> Importar</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/contacts/new"><Plus className="mr-2 h-4 w-4" /> Nuevo contacto</Link>
          </Button>
        </div>
      </div>

      <ContactFiltersBar
        filters={{ ...filters, search: search || undefined }}
        onChange={(f) => setFilters({ ...filters, ...f, page: 1 })}
      />

      <input
        type="search"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Buscar contactos..."
        className="hidden"
        aria-hidden="true"
      />

      {!loading && items.length === 0 ? (
        <Card>
          <CardContent className="py-10">
            <EmptyState
              title="No hay contactos aún"
              description="Crea tu primer contacto o importa un CSV para empezar."
              icon={<UsersIcon className="h-6 w-6" />}
              actionLabel="Crear contacto"
              onAction={() => (window.location.href = "/contacts/new")}
            />
          </CardContent>
        </Card>
      ) : (
        <ContactTable
          contacts={items}
          loading={loading}
          total={total}
          page={filters.page ?? 1}
          pageSize={filters.page_size ?? 20}
          onDelete={setToDelete}
        />
      )}

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Eliminar contacto"
        description={`¿Seguro que quieres eliminar a ${toDelete?.first_name ?? ""} ${toDelete?.last_name ?? ""}? Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        cancelLabel="Cancelar"
        destructive
        loading={deleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}
