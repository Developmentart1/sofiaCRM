"use client";

import * as React from "react";
import { useEffect, useState } from "react";
import { reportsApi } from "@/lib/api/reports";
import { tasksApi } from "@/lib/api/tasks";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { RecentActivity } from "@/components/dashboard/recent-activity";
import { UpcomingTasks } from "@/components/dashboard/upcoming-tasks";
import { StuckOpportunities } from "@/components/dashboard/stuck-opportunities";
import { PerformanceByUser } from "@/components/dashboard/performance-by-user";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, CartesianGrid } from "recharts";
import { useAuth } from "@/lib/hooks/use-auth";
import type { Activity, DashboardKPIs, Opportunity, Task, UserPerformance } from "@/lib/types/api";
import { formatCurrency } from "@/lib/utils/format";

export default function DashboardPage() {
  const { user } = useAuth();
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stuck, setStuck] = useState<Opportunity[]>([]);
  const [performance, setPerformance] = useState<UserPerformance[]>([]);
  const [loading, setLoading] = useState(true);

  const [trendData, setTrendData] = useState<Array<{ date: string; value: number }>>([]);
  const [pipelineData, setPipelineData] = useState<Array<{ stage_name: string; count: number }>>([]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      try {
        const [k, a, t, s, p, trend, pipeline] = await Promise.allSettled([
          reportsApi.kpis(),
          reportsApi.recentActivity(8),
          reportsApi.upcomingTasks(8),
          reportsApi.stuckOpportunities(),
          reportsApi.performanceByUser({}),
          reportsApi.getPipelineTrend({ days: 7 }),
          reportsApi.getPipelineStageDistribution(),
        ]);
        if (!mounted) return;
        if (k.status === "fulfilled") setKpis(k.value);
        if (a.status === "fulfilled") setActivities(a.value);
        if (t.status === "fulfilled") setTasks(t.value);
        if (s.status === "fulfilled") setStuck(s.value);
        if (p.status === "fulfilled") setPerformance(p.value);
        if (trend.status === "fulfilled") setTrendData(trend.value);
        if (pipeline.status === "fulfilled") setPipelineData(pipeline.value);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handleComplete = async (id: string) => {
    try {
      await tasksApi.complete(id);
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch {
      // toast
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-black tracking-tight">Hola, {user?.full_name?.split(" ")[0] ?? "equipo"}.</h1>
        <p className="mt-1 text-sm text-muted-foreground">Resumen operativo de tu equipo para hoy.</p>
      </div>

      <KpiGrid kpis={kpis} loading={loading} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Actividad del pipeline (últimos 7 días)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" className="text-xs" />
                  <YAxis className="text-xs" tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "hsl(var(--background))", border: "1px solid hsl(var(--border))" }}
                    formatter={(v: number) => formatCurrency(v)}
                  />
                  <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Oportunidades por etapa</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pipelineData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="stage_name" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip contentStyle={{ backgroundColor: "hsl(var(--background))", border: "1px solid hsl(var(--border))" }} />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <UpcomingTasks tasks={tasks} loading={loading} onComplete={handleComplete} />
        <RecentActivity activities={activities} loading={loading} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <StuckOpportunities opportunities={stuck} loading={loading} />
        <PerformanceByUser data={performance} loading={loading} />
      </div>
    </div>
  );
}
