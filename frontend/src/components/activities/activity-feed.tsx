"use client";

import * as React from "react";
import { Phone, Mail, Calendar, FileText, MessageCircle, MoreHorizontal, Trash2 } from "lucide-react";
import type { Activity, ActivityType } from "@/lib/types/api";
import { formatDateTime, formatRelative } from "@/lib/utils/format";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils/cn";
import { EmptyState } from "@/components/common/empty-state";

const iconMap: Record<ActivityType, React.ElementType> = {
  note: FileText,
  call: Phone,
  email: Mail,
  meeting: Calendar,
  sms: MessageCircle,
  whatsapp: MessageCircle,
  task_completed: FileText,
  stage_change: FileText,
  created: FileText,
  updated: FileText,
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

interface ActivityFeedProps {
  activities: Activity[];
  loading?: boolean;
  onDelete?: (id: string) => void;
  className?: string;
}

export function ActivityFeed({ activities, loading, onDelete, className }: ActivityFeedProps) {
  if (loading) {
    return (
      <div className={cn("space-y-2", className)}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse rounded-md bg-muted" />
        ))}
      </div>
    );
  }
  if (activities.length === 0) {
    return (
      <EmptyState
        title="Sin actividad"
        description="Registra tu primera nota, llamada o email."
        icon={<FileText className="h-5 w-5" />}
        className={className}
      />
    );
  }
  return (
    <ol className={cn("relative space-y-3", className)}>
      {activities.map((a) => {
        const Icon = iconMap[a.type] ?? FileText;
        const color = colorMap[a.type] ?? "bg-slate-500/10 text-slate-600";
        return (
          <li key={a.id} className="flex gap-3 rounded-md border p-3">
            <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-full", color)}>
              <Icon className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-medium">{a.subject}</p>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-xs text-muted-foreground" title={formatDateTime(a.occurred_at)}>
                    {formatRelative(a.occurred_at)}
                  </span>
                  {onDelete && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" aria-label="Más" className="h-6 w-6">
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onDelete(a.id)} className="text-destructive focus:text-destructive">
                          <Trash2 className="mr-2 h-3.5 w-3.5" /> Eliminar
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </div>
              {a.body && <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">{a.body}</p>}
              <div className="mt-1 text-xs text-muted-foreground">
                {a.user_name && <span>por {a.user_name}</span>}
                {a.duration_minutes ? <span> · {a.duration_minutes} min</span> : null}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
