"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { reportsApi } from "@/lib/api/reports";
import type { DashboardKPIs, ReportSummary, UserPerformance } from "@/lib/types/api";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils/format";

export default function ReportsPage() {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [performance, setPerformance] = useState<UserPerformance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      try {
        const [k, s, p] = await Promise.allSettled([
          reportsApi.kpis(),
          reportsApi.summary({}),
          reportsApi.performanceByUser({}),
        ]);
        if (!mounted) return;
        if (k.status === "fulfilled") setKpis(k.value);
        if (s.status === "fulfilled") setSummary(s.value);
        if (p.status === "fulfilled") setPerformance(p.value);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <div className="p-8 text-muted-foreground">Cargando...</div>;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Reportes</h1>
        <p className="text-sm text-muted-foreground">Métricas agregadas de tu organización.</p>
      </div>

      <KpiGrid kpis={kpis} loading={false} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ingresos por pipeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {summary?.revenue_by_pipeline.length ? (
              summary.revenue_by_pipeline.map((r) => (
                <div key={r.pipeline_id} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{r.pipeline_name}</span>
                  <span className="font-medium">{formatCurrency(r.revenue)}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">Sin datos en el periodo.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ingresos por responsable</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {summary?.revenue_by_owner.length ? (
              summary.revenue_by_owner.map((r) => (
                <div key={r.user_id} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{r.user_name}</span>
                  <span className="font-medium">{formatCurrency(r.revenue)}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">Sin datos en el periodo.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Desempeño por usuario</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {performance.length ? (
            performance.map((p) => (
              <div key={p.user_id} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{p.user_name}</span>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span>Ganadas: {p.opportunities_won}</span>
                  <span>Valor: {formatCurrency(p.opportunities_won_value)}</span>
                  <span>Abiertas: {p.opportunities_open}</span>
                  <span>Tareas: {p.tasks_completed}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">Sin usuarios.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
