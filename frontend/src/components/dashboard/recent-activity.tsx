"use client";

import * as React from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Phone, Mail, Calendar, FileText, CheckCircle2, ArrowRight, User, Building2, Target } from "lucide-react";
import type { Activity, ActivityType } from "@/lib/types/api";
import { formatRelative } from "@/lib/utils/format";
import { EmptyState } from "@/components/common/empty-state";

const iconMap: Record<ActivityType, React.ElementType> = {
  note: FileText,
  call: Phone,
  email: Mail,
  meeting: Calendar,
  sms: Phone,
  whatsapp: Phone,
  task_completed: CheckCircle2,
  stage_change: ArrowRight,
  created: User,
  updated: User,
};

const colorMap: Record<ActivityType, string> = {
  note: "bg-slate-500/10 text-slate-600",
  call: "bg-blue-500/10 text-blue-600",
  email: "bg-amber-500/10 text-amber-600",
  meeting: "bg-purple-500/10 text-purple-600",
  sms: "bg-emerald-500/10 text-emerald-600",
  whatsapp: "bg-emerald-500/10 text-emerald-600",
  task_completed: "bg-emerald-500/10 text-emerald-600",
  stage_change: "bg-indigo-500/10 text-indigo-600",
  created: "bg-slate-500/10 text-slate-600",
  updated: "bg-slate-500/10 text-slate-600",
};

interface RecentActivityProps {
  activities: Activity[];
  loading?: boolean;
}

export function RecentActivity({ activities, loading }: RecentActivityProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">Actividad reciente</CardTitle>
        <Link href="/activities" className="text-xs text-muted-foreground hover:text-foreground">
          Ver todo
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : activities.length === 0 ? (
          <div className="p-4">
            <EmptyState title="Sin actividad reciente" description="La actividad del equipo aparecerá aquí." />
          </div>
        ) : (
          <ul className="divide-y">
            {activities.map((a) => {
              const Icon = (iconMap[a.type] ?? FileText) as React.ElementType;
              const color = colorMap[a.type] ?? "bg-slate-500/10 text-slate-600";
              return (
                <li key={a.id} className="flex items-start gap-3 px-4 py-3">
                  <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${color}`}>
                    <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-medium">{a.subject}</p>
                      <span className="shrink-0 text-xs text-muted-foreground">{formatRelative(a.occurred_at)}</span>
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      {a.user_name && <span>{a.user_name}</span>}
                      {a.contact_name && (
                        <Link href={`/contacts/${a.contact_id}`} className="inline-flex items-center gap-1 hover:text-foreground">
                          <User className="h-3 w-3" /> {a.contact_name}
                        </Link>
                      )}
                      {a.opportunity_name && a.opportunity_id && (
                        <Link href={`/opportunities/${a.opportunity_id}`} className="inline-flex items-center gap-1 hover:text-foreground">
                          <Target className="h-3 w-3" /> {a.opportunity_name}
                        </Link>
                      )}
                      {a.company_name && a.company_id && (
                        <Link href={`/companies/${a.company_id}`} className="inline-flex items-center gap-1 hover:text-foreground">
                          <Building2 className="h-3 w-3" /> {a.company_name}
                        </Link>
                      )}
                    </div>
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
