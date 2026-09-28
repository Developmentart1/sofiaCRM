"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { opportunitiesApi, pipelinesApi } from "@/lib/api/opportunities";
import type { Opportunity, PipelineStage } from "@/lib/types/api";

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"kanban" | "table">("kanban");

  useEffect(() => {
    Promise.all([
      opportunitiesApi.list({}),
      pipelinesApi.list(),
    ]).then(async ([opps, pipes]) => {
      const allOpps = "items" in opps ? (opps as { items: Opportunity[] }).items : (opps as unknown as Opportunity[]);
      const list = Array.isArray(allOpps) ? allOpps : [];
      setOpportunities(list);
      if (pipes.length > 0 && pipes[0]) {
        try {
          const detail = await pipelinesApi.get(pipes[0].id);
          const stageList = (detail as unknown as { stages?: PipelineStage[] }).stages;
          setStages(stageList ?? []);
        } catch { setStages([]); }
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-muted-foreground">Cargando...</div>;

  const oppsByStage: Record<string, Opportunity[]> = {};
  for (const s of stages) oppsByStage[s.id] = [];
  for (const o of opportunities) {
    const sid = o.stage_id;
    if (sid && oppsByStage[sid]) oppsByStage[sid].push(o);
  }

  const totalValue = opportunities.reduce((s, o) => s + (o.estimated_value || 0), 0);
  const openCount = opportunities.filter(o => o.status === "open").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Oportunidades</h1>
          <p className="text-sm text-muted-foreground">
            {openCount} abiertas · {opportunities.length} total · ${totalValue.toLocaleString()} MXN
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setView(view === "kanban" ? "table" : "kanban")}
            className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted">
            {view === "kanban" ? "📋 Tabla" : "📌 Kanban"}
          </button>
          <Link href="/opportunities/new"
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:opacity-90">
            + Nueva
          </Link>
        </div>
      </div>

      {view === "kanban" && (
        <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: "60vh" }}>
          {stages.map((stage) => {
            const cards = oppsByStage[stage.id] ?? [];
            return (
              <div key={stage.id} className="flex-shrink-0 w-72 bg-muted/40 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">{stage.name}</h3>
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">{cards.length}</span>
                </div>
                <div className="space-y-2">
                  {cards.map((opp) => (
                    <Link key={opp.id} href={`/opportunities/${opp.id}`}
                      className="block bg-card border rounded-lg p-3 hover:shadow-md transition-shadow">
                      <p className="text-sm font-medium truncate">{opp.name}</p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-muted-foreground">${(opp.estimated_value || 0).toLocaleString()}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded-full bg-muted">{opp.probability}%</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {view === "table" && (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 font-medium">Nombre</th>
                <th className="text-left p-3 font-medium">Etapa</th>
                <th className="text-right p-3 font-medium">Valor</th>
                <th className="text-right p-3 font-medium">Prob.</th>
                <th className="text-center p-3 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {opportunities.map((opp) => {
                const stageName = stages.find(s => s.id === opp.stage_id)?.name ?? "—";
                return (
                  <tr key={opp.id} className="border-t hover:bg-muted/30">
                    <td className="p-3">
                      <Link href={`/opportunities/${opp.id}`} className="font-medium hover:underline">{opp.name}</Link>
                    </td>
                    <td className="p-3 text-muted-foreground">{stageName}</td>
                    <td className="p-3 text-right">${(opp.estimated_value || 0).toLocaleString()}</td>
                    <td className="p-3 text-right">{opp.probability}%</td>
                    <td className="p-3 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        opp.status === "won" ? "bg-green-100 text-green-700" :
                        opp.status === "lost" ? "bg-red-100 text-red-700" :
                        "bg-blue-100 text-blue-700"
                      }`}>{opp.status}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
