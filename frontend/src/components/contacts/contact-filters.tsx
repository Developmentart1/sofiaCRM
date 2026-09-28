"use client";

import * as React from "react";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { SearchInput } from "@/components/common/search-input";
import type { ContactFilters } from "@/lib/types/api";
import { Filter } from "lucide-react";

interface ContactFiltersBarProps {
  filters: ContactFilters;
  onChange: (filters: ContactFilters) => void;
}

export function ContactFiltersBar({ filters, onChange }: ContactFiltersBarProps) {
  const [search, setSearch] = useState(filters.search ?? "");
  return (
    <Card>
      <CardContent className="flex flex-wrap items-center gap-2 p-3">
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Buscar por nombre, email o teléfono..."
          className="w-full sm:max-w-xs"
        />
        <Select
          value={filters.status ?? "all"}
          onValueChange={(v) => onChange({ ...filters, status: v === "all" ? undefined : (v as ContactFilters["status"]), page: 1 })}
        >
          <SelectTrigger className="w-36" aria-label="Estado">
            <Filter className="mr-1 h-3.5 w-3.5" />
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los estados</SelectItem>
            <SelectItem value="lead">Lead</SelectItem>
            <SelectItem value="active">Activo</SelectItem>
            <SelectItem value="customer">Cliente</SelectItem>
            <SelectItem value="inactive">Inactivo</SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setSearch("");
            onChange({ page: 1 });
          }}
        >
          Limpiar
        </Button>
        <div className="ml-auto text-xs text-muted-foreground">
          {search !== (filters.search ?? "") ? "Aplicando búsqueda..." : "Filtros sincronizados"}
        </div>
      </CardContent>
    </Card>
  );
}
