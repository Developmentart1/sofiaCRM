"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { pipelinesApi } from "@/lib/api/opportunities";
import type { Pipeline } from "@/lib/types/api";

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    pipelinesApi.list().then((p) => { setPipelines(p); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-muted-foreground">Cargando...</div>;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Pipelines</h1>
        <Link href="/pipelines/new" className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm">+ Nuevo</Link>
      </div>
      <div className="grid gap-4">
        {pipelines.map((p) => (
          <Link key={p.id} href={`/pipelines/${p.id}`} className="border rounded-lg p-4 hover:shadow-md">
            <p className="font-medium">{p.name}</p>
            {p.description && <p className="text-sm text-muted-foreground mt-1">{p.description}</p>}
          </Link>
        ))}
      </div>
    </div>
  );
}
