"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ContactForm } from "@/components/contacts/contact-form";
import { useContacts, useCompanies } from "@/lib/hooks/use-contacts";
import { useDebounce } from "@/lib/hooks/use-debounce";
import { useState } from "react";

export default function NewContactPage() {
  const router = useRouter();
  const { create } = useContacts({ page: 1, page_size: 1 });
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);
  const { items: companies } = useCompanies({ search: debouncedSearch || undefined, page: 1, page_size: 50 });

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center gap-2">
        <Link href="/contacts" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
          <ArrowLeft className="h-4 w-4" /> Contactos
        </Link>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Nuevo contacto</CardTitle>
        </CardHeader>
        <CardContent>
          <ContactForm
            companies={companies}
            onSubmit={async (data) => {
              const payload = {
                ...data,
                company_id: data.company_id || null,
                email: data.email || null,
                phone: data.phone || null,
                job_title: data.job_title || null,
                source: data.source || null,
                notes: data.notes || null,
              };
              const c = await create(payload);
              router.push(`/contacts/${c.id}`);
            }}
            onCancel={() => router.back()}
            submitLabel="Crear contacto"
          />
        </CardContent>
      </Card>
    </div>
  );
}
