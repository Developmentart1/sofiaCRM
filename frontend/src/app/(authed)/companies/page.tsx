"use client";

import { useEffect, useState } from "react";
import { companiesApi } from "@/lib/api/companies";
import type { Company } from "@/lib/types/api";

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  useEffect(() => {
    companiesApi.list({}).then((r) => {
      const items = "items" in r ? (r as { items: Company[] }).items : (r as unknown as Company[]);
      setCompanies(Array.isArray(items) ? items : []);
    }).catch(() => {});
  }, []);
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Empresas</h1>
      <div className="space-y-2">{companies.map((c) => <div key={c.id} className="border rounded p-3 text-sm font-medium">{c.name}</div>)}</div>
    </div>
  );
}
