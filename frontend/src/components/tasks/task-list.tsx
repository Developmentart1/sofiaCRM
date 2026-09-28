"use client";

import * as React from "react";
import { useState } from "react";
import Link from "next/link";
import { Plus, CheckCircle2, Circle, ListTodo } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { EmptyState } from "@/components/common/empty-state";
import { TaskForm } from "./task-form";
import { useTasks } from "@/lib/hooks/use-tasks";
import { formatDate, formatRelative } from "@/lib/utils/format";
import type { Task } from "@/lib/types/api";
import type { TaskInput } from "@/lib/utils/validation";

interface TaskListProps {
  contactId?: string;
  opportunityId?: string;
  companyId?: string;
  ownerId?: string;
  showCreate?: boolean;
}

const priorityColor: Record<Task["priority"], "default" | "warning" | "destructive" | "info"> = {
  low: "info",
  medium: "default",
  high: "warning",
  urgent: "destructive",
};

const statusVariant: Record<Task["status"], "default" | "success" | "secondary" | "destructive"> = {
  pending: "default",
  in_progress: "default",
  completed: "success",
  cancelled: "secondary", overdue: "destructive",
};

export function TaskList({ contactId, opportunityId, companyId, ownerId, showCreate = true }: TaskListProps) {
  const { items, loading, create, complete, remove } = useTasks({
    page: 1,
    page_size: 50,
    contact_id: contactId,
    opportunity_id: opportunityId,
    company_id: companyId,
    owner_id: ownerId,
  });
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async (data: TaskInput) => {
    setSubmitting(true);
    try {
      await create({
        ...data,
        contact_id: contactId ?? data.contact_id ?? null,
        opportunity_id: opportunityId ?? data.opportunity_id ?? null,
        company_id: companyId ?? data.company_id ?? null,
      });
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="h-24 animate-pulse rounded-md bg-muted" />;
  }

  return (
    <div className="space-y-2">
      {showCreate && (
        <div className="flex justify-end">
          <Button size="sm" onClick={() => setOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> Nueva tarea
          </Button>
        </div>
      )}
      {items.length === 0 ? (
        <EmptyState
          title="Sin tareas"
          description="No hay tareas asociadas."
          icon={<ListTodo className="h-5 w-5" />}
        />
      ) : (
        <ul className="space-y-2">
          {items.map((t) => (
            <li key={t.id}>
              <Card>
                <CardContent className="flex items-start gap-3 p-3">
                  <button
                    onClick={() => void complete(t.id)}
                    aria-label={t.status === "completed" ? "Reabrir" : "Completar"}
                    className="mt-0.5 text-muted-foreground hover:text-emerald-600"
                  >
                    {t.status === "completed" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Circle className="h-4 w-4" />}
                  </button>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className={`text-sm font-medium ${t.status === "completed" ? "line-through text-muted-foreground" : ""}`}>{t.title}</p>
                      <Badge variant={statusVariant[t.status]} className="text-[10px]">{t.status}</Badge>
                      <Badge variant={priorityColor[t.priority]} className="text-[10px]">{t.priority}</Badge>
                    </div>
                    {t.description && <p className="mt-0.5 text-sm text-muted-foreground">{t.description}</p>}
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t.due_date && <span>Vence {formatDate(t.due_date)} ({formatRelative(t.due_date)})</span>}
                      {t.contact_name && t.contact_id && !contactId && (
                        <span> · <Link href={`/contacts/${t.contact_id}`} className="hover:underline">{t.contact_name}</Link></span>
                      )}
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => void remove(t.id)} aria-label="Eliminar">
                    Eliminar
                  </Button>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva tarea</DialogTitle>
          </DialogHeader>
          <TaskForm
            onSubmit={handleCreate}
            onCancel={() => setOpen(false)}
            loading={submitting}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
