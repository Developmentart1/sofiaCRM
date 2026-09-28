"use client";

import * as React from "react";
import Link from "next/link";
import { type ColumnDef } from "@tanstack/react-table";
import { Mail, Phone, Building2, MoreHorizontal } from "lucide-react";
import { DataTable } from "@/components/common/data-table";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { formatDate, fullName, initials } from "@/lib/utils/format";
import type { Contact, ContactStatus } from "@/lib/types/api";

const statusVariant: Record<ContactStatus, "default" | "success" | "warning" | "info" | "secondary"> = {
  active: "success",
  customer: "default",
  lead: "info",
  inactive: "secondary",
};

interface ContactTableProps {
  contacts: Contact[];
  loading?: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange?: (page: number) => void;
  onDelete?: (contact: Contact) => void;
}

export function ContactTable({ contacts, loading, onDelete }: ContactTableProps) {
  const columns = React.useMemo<ColumnDef<Contact, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Nombre",
        accessorFn: (r) => fullName(r.first_name, r.last_name),
        cell: ({ row }) => {
          const c = row.original;
          return (
            <Link href={`/contacts/${c.id}`} className="flex items-center gap-2 hover:opacity-80">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-[10px]">
                  {initials(c.first_name, c.last_name)}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{fullName(c.first_name, c.last_name)}</p>
                {c.job_title && <p className="truncate text-xs text-muted-foreground">{c.job_title}</p>}
              </div>
            </Link>
          );
        },
        enableSorting: true,
      },
      {
        id: "email",
        header: "Email",
        accessorFn: (r) => r.email ?? "",
        cell: ({ row }) =>
          row.original.email ? (
            <a href={`mailto:${row.original.email}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
              <Mail className="h-3 w-3" />
              {row.original.email}
            </a>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: "phone",
        header: "Teléfono",
        accessorFn: (r) => r.phone ?? "",
        cell: ({ row }) =>
          row.original.phone ? (
            <a href={`tel:${row.original.phone}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
              <Phone className="h-3 w-3" />
              {row.original.phone}
            </a>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: "company",
        header: "Empresa",
        cell: ({ row }) =>
          row.original.company_id ? (
            <Link href={`/companies/${row.original.company_id}`} className="inline-flex items-center gap-1 text-sm hover:opacity-80">
              <Building2 className="h-3 w-3" />
              {row.original.company_name ?? "—"}
            </Link>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        id: "status",
        header: "Estado",
        cell: ({ row }) => <Badge variant={statusVariant[row.original.status]}>{row.original.status}</Badge>,
      },
      {
        id: "created_at",
        header: "Creado",
        accessorFn: (r) => r.created_at,
        cell: ({ row }) => <span className="text-xs text-muted-foreground">{formatDate(row.original.created_at)}</span>,
        enableSorting: true,
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Acciones" className="h-7 w-7">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/contacts/${row.original.id}`}>Ver detalle</Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/contacts/${row.original.id}#edit`}>Editar</Link>
              </DropdownMenuItem>
              {onDelete && (
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => onDelete(row.original)}
                >
                  Eliminar
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        ),
      },
    ],
    [onDelete]
  );

  return (
    <DataTable
      columns={columns}
      data={contacts}
      loading={loading}
      getRowId={(r) => r.id}
      onRowClick={(r) => {
        if (typeof window !== "undefined") {
          window.location.href = `/contacts/${r.id}`;
        }
      }}
    />
  );
}
