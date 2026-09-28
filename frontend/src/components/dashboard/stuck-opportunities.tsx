"use client";

import * as React from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle } from "lucide-react";
import type { Opportunity } from "@/lib/types/api";
import { formatCurrency, formatRelative } from "@/lib/utils/format";
import { EmptyState } from "@/components/common/empty-state";
import { Badge } from "@/components/ui/badge";

interface StuckOpportunitiesProps {
  opportunities: Opportunity[];
  loading?: boolean;
}

export function StuckOpportunities({ opportunities, loading }: StuckOpportunitiesProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">Oportunidades estancadas</CardTitle>
        <Link href="/opportunities?view=stuck" className="text-xs text-muted-foreground hover:text-foreground">
          Ver todas
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : opportunities.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="Nada estancado"
              description="Todas tus oportunidades están en movimiento."
              icon={<AlertTriangle className="h-5 w-5" />}
            />
          </div>
        ) : (
          <ul className="divide-y">
            {opportunities.slice(0, 6).map((o) => (
              <li key={o.id} className="px-4 py-3">
                <Link href={`/opportunities/${o.id}`} className="block hover:opacity-80">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-medium">{o.name}</p>
                    <span className="text-sm font-semibold">{formatCurrency(o.estimated_value, o.currency)}</span>
                  </div>
                  <div className="mt-0.5 flex items-center justify-between gap-2 text-xs text-muted-foreground">
                    <span>
                      {"Etapa"} · {o.contact_id ?? o.company_id ?? "—"}
                    </span>
                    {o.entered_stage_at !== null && (
                      <Badge variant="warning" className="text-[10px]">
                        Sin movimiento
                      </Badge>
                    )}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
