"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { UserPerformance } from "@/lib/types/api";
import { formatCurrency, formatNumber, initials } from "@/lib/utils/format";
import { EmptyState } from "@/components/common/empty-state";
import { Users } from "lucide-react";

interface PerformanceByUserProps {
  data: UserPerformance[];
  loading?: boolean;
}

export function PerformanceByUser({ data, loading }: PerformanceByUserProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">Rendimiento por vendedor</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : data.length === 0 ? (
          <EmptyState title="Sin datos" description="Aún no hay rendimiento que mostrar." icon={<Users className="h-5 w-5" />} />
        ) : (
          <ul className="space-y-3">
            {data.slice(0, 6).map((u) => {
              const parts = u.user_name.split(" ");
              return (
                <li key={u.user_id} className="flex items-center gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback>{initials(parts[0] ?? "", parts[1] ?? "")}</AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{u.user_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatNumber(u.opportunities_won)} ganadas · {formatNumber(u.tasks_completed)} tareas
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold">{formatCurrency(u.opportunities_won_value)}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
