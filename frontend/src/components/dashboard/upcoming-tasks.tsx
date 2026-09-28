"use client";

import * as React from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ListTodo, Clock } from "lucide-react";
import type { Task } from "@/lib/types/api";
import { formatDate, formatRelative } from "@/lib/utils/format";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/common/empty-state";
import { Checkbox } from "@/components/ui/checkbox";

interface UpcomingTasksProps {
  tasks: Task[];
  loading?: boolean;
  onComplete?: (id: string) => void;
}

const priorityColor: Record<Task["priority"], "default" | "warning" | "destructive" | "info"> = {
  low: "info",
  medium: "default",
  high: "warning",
  urgent: "destructive",
};

export function UpcomingTasks({ tasks, loading, onComplete }: UpcomingTasksProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">Próximas tareas</CardTitle>
        <Link href="/tasks" className="text-xs text-muted-foreground hover:text-foreground">
          Ver todas
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-md bg-muted" />
            ))}
          </div>
        ) : tasks.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="Sin tareas pendientes"
              description="Estás al día. Tómate un café ☕"
              icon={<ListTodo className="h-5 w-5" />}
            />
          </div>
        ) : (
          <ul className="divide-y">
            {tasks.map((t) => (
              <li key={t.id} className="flex items-start gap-3 px-4 py-3">
                <Checkbox
                  checked={t.status === "completed"}
                  onCheckedChange={() => onComplete?.(t.id)}
                  aria-label={`Marcar tarea ${t.title} como completada`}
                  className="mt-1"
                />
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-medium ${t.status === "completed" ? "line-through text-muted-foreground" : ""}`}>
                    {t.title}
                  </p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <Badge variant={priorityColor[t.priority]} className="text-[10px]">
                      {t.priority}
                    </Badge>
                    {t.due_date && (
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatRelative(t.due_date)}
                      </span>
                    )}
                    {t.contact_id && t.contact_name && (
                      <Link href={`/contacts/${t.contact_id}`} className="hover:text-foreground">
                        {t.contact_name}
                      </Link>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
