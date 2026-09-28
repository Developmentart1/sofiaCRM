"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { contactsApi } from "@/lib/api/contacts";
import type { Contact } from "@/lib/types/api";
import Link from "next/link";
import { useDebounce } from "@/lib/hooks/use-debounce";

interface DuplicateWarningProps {
  email?: string;
  phone?: string;
  excludeId?: string;
}

export function DuplicateWarning({ email, phone, excludeId }: DuplicateWarningProps) {
  const [duplicates, setDuplicates] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(false);
  const debouncedEmail = useDebounce(email, 400);
  const debouncedPhone = useDebounce(phone, 400);

  useEffect(() => {
    let cancelled = false;
    async function check() {
      if (!debouncedEmail && !debouncedPhone) {
        setDuplicates([]);
        return;
      }
      setLoading(true);
      try {
        const result = await contactsApi.checkDuplicates({
          email: debouncedEmail || undefined,
          phone: debouncedPhone || undefined,
        });
        if (!cancelled) {
          setDuplicates(result.filter((c) => c.id !== excludeId));
        }
      } catch {
        if (!cancelled) setDuplicates([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void check();
    return () => {
      cancelled = true;
    };
  }, [debouncedEmail, debouncedPhone, excludeId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /> Verificando duplicados...
      </div>
    );
  }
  if (duplicates.length === 0) return null;
  return (
    <div role="alert" className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" />
      <div className="flex-1">
        <p className="font-medium text-amber-700 dark:text-amber-300">Posibles duplicados encontrados</p>
        <ul className="mt-1 space-y-0.5 text-amber-700/90 dark:text-amber-300/90">
          {duplicates.slice(0, 3).map((c) => (
            <li key={c.id}>
              <Link href={`/contacts/${c.id}`} className="hover:underline" target="_blank">
                {c.first_name} {c.last_name} {c.email ? `· ${c.email}` : ""}
              </Link>
            </li>
          ))}
          {duplicates.length > 3 && <li>...y {duplicates.length - 3} más</li>}
        </ul>
      </div>
    </div>
  );
}
