"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { tasksApi } from "@/lib/api/tasks";
import type { Task } from "@/lib/types/api";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    tasksApi.list({ view: "today" }).then((res) => {
      const items = "items" in res ? (res as { items: Task[] }).items : (res as unknown as Task[]);
      setTasks(Array.isArray(items) ? items : []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-muted-foreground">Cargando...</div>;

  const overdue = tasks.filter(t => t.status === "overdue");
  const today = tasks.filter(t => t.status !== "overdue" && t.status !== "completed");
  const completed = tasks.filter(t => t.status === "completed");

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Mis Tareas</h1>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="font-bold text-red-700">{overdue.length}</p>
          <p className="text-red-600">Vencidas</p>
        </div>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="font-bold text-blue-700">{today.length}</p>
          <p className="text-blue-600">Pendientes</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="font-bold text-green-700">{completed.length}</p>
          <p className="text-green-600">Completadas</p>
        </div>
      </div>
      <div className="space-y-2">
        {tasks.map((t) => (
          <div key={t.id} className="border rounded-lg p-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">{t.title}</p>
              <p className="text-xs text-muted-foreground">{t.due_date ?? "Sin fecha"}</p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              t.status === "overdue" ? "bg-red-100 text-red-700" :
              t.status === "completed" ? "bg-green-100 text-green-700" :
              "bg-blue-100 text-blue-700"
            }`}>{t.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
