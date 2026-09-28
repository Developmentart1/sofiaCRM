import * as React from "react";
import { KpiCard } from "./kpi-card";
import { Users, Building2, Target, DollarSign, TrendingUp, Clock, CheckCircle2, AlertCircle } from "lucide-react";
import type { DashboardKPIs } from "@/lib/types/api";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils/format";

interface KpiGridProps {
  kpis: DashboardKPIs | null;
  loading?: boolean;
}

export function KpiGrid({ kpis, loading }: KpiGridProps) {
  if (loading || !kpis) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg border bg-card" />
        ))}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard label="Contactos" value={formatNumber(kpis.total_contacts)} icon={Users} />
      <KpiCard label="Empresas" value={formatNumber(kpis.total_companies)} icon={Building2} />
      <KpiCard label="Oportunidades abiertas" value={formatNumber(kpis.total_opportunities)} icon={Target} />
      <KpiCard
        label="Pipeline abierto"
        value={formatCurrency(kpis.open_opportunities_value)}
        icon={DollarSign}
      />
      <KpiCard
        label="Ganado este mes"
        value={formatCurrency(kpis.won_opportunities_value)}
        icon={CheckCircle2}
      />
      <KpiCard
        label="Tasa de conversión"
        value={formatPercent(kpis.conversion_rate)}
        icon={TrendingUp}
      />
      <KpiCard
        label="Tamaño promedio"
        value={formatCurrency(kpis.average_deal_size)}
        icon={DollarSign}
      />
      <KpiCard
        label="Tareas vencidas"
        value={formatNumber(kpis.overdue_tasks)}
        icon={AlertCircle}
        iconClassName="bg-rose-500/10 text-rose-600"
      />
    </div>
  );
}
