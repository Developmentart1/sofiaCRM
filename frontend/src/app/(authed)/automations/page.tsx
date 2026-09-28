"use client";

import { useCallback, useEffect, useState } from "react";
import { Zap } from "lucide-react";
import { automationsApi } from "@/lib/api/automations";
import type {
  AutomationCondition,
  AutomationExecution,
  AutomationOperator,
  AutomationRuleRead,
} from "@/lib/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils/cn";

const EVENT_TYPES = [
  "contact.created",
  "contact.updated",
  "contact.merged",
  "company.created",
  "company.updated",
  "pipeline.created",
  "stage.created",
  "opportunity.created",
  "opportunity.stage_changed",
  "opportunity.assignee_changed",
  "opportunity.value_changed",
  "opportunity.won",
  "opportunity.lost",
  "opportunity.discarded",
  "task.created",
  "task.completed",
  "task.overdue",
  "activity.created",
  "document.uploaded",
];

const OPERATORS: AutomationOperator[] = ["eq", "neq", "contains", "gt", "lt"];

const ACTION_TYPES = ["create_task", "create_activity", "move_stage", "update_field"];

const UPDATE_FIELDS = [
  "opportunity.estimated_value",
  "opportunity.priority",
  "opportunity.assigned_user_id",
  "contact.email",
  "contact.phone",
  "contact.status",
];

interface ConditionDraft {
  field: string;
  op: AutomationOperator;
  value: string;
}

interface ActionDraft {
  action_type: string;
  title: string;
  priority: string;
  due_offset_days: string;
  assigned_user_id: string;
  activity_type: string;
  subject: string;
  stage_id: string;
  field: string;
  value: string;
}

const emptyAction = (action_type = "create_task"): ActionDraft => ({
  action_type,
  title: "",
  priority: "medium",
  due_offset_days: "",
  assigned_user_id: "",
  activity_type: "note",
  subject: "",
  stage_id: "",
  field: "opportunity.estimated_value",
  value: "",
});

function buildConfig(a: ActionDraft): Record<string, unknown> {
  switch (a.action_type) {
    case "create_task": {
      const config: Record<string, unknown> = { title: a.title || "Tarea", priority: a.priority || "medium" };
      if (a.due_offset_days.trim() !== "") config.due_offset_days = Number(a.due_offset_days);
      if (a.assigned_user_id.trim() !== "") config.assigned_user_id = a.assigned_user_id.trim();
      return config;
    }
    case "create_activity":
      return { type: a.activity_type, subject: a.subject || "Actividad" };
    case "move_stage":
      return { stage_id: a.stage_id };
    case "update_field":
      return { field: a.field, value: a.value };
    default:
      return {};
  }
}

function statusBadge(status: string) {
  const map: Record<string, "success" | "destructive" | "warning" | "secondary"> = {
    success: "success",
    failed: "destructive",
    skipped: "warning",
    pending: "secondary",
  };
  return <Badge variant={map[status] ?? "secondary"}>{status}</Badge>;
}

export default function AutomationsPage() {
  const [rules, setRules] = useState<AutomationRuleRead[]>([]);
  const [executions, setExecutions] = useState<AutomationExecution[]>([]);
  const [view, setView] = useState<"rules" | "executions">("rules");
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [trigger, setTrigger] = useState("contact.created");
  const [maxDepth, setMaxDepth] = useState("5");
  const [conditions, setConditions] = useState<ConditionDraft[]>([]);
  const [actions, setActions] = useState<ActionDraft[]>([emptyAction()]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [r, e] = await Promise.all([automationsApi.listRules(), automationsApi.listExecutions({ page_size: 50 })]);
      setRules(r);
      setExecutions(e.items);
    } catch {
      // handled below
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const resetForm = () => {
    setName("");
    setTrigger("contact.created");
    setMaxDepth("5");
    setConditions([]);
    setActions([emptyAction()]);
    setError(null);
  };

  const openBuilder = () => {
    resetForm();
    setDialogOpen(true);
  };

  const addCondition = () =>
    setConditions((c) => [...c, { field: "", op: "eq", value: "" }]);
  const updateCondition = (i: number, patch: Partial<ConditionDraft>) =>
    setConditions((c) => c.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  const removeCondition = (i: number) => setConditions((c) => c.filter((_, idx) => idx !== i));

  const addAction = () => setActions((a) => [...a, emptyAction()]);
  const updateAction = (i: number, patch: Partial<ActionDraft>) =>
    setActions((a) => a.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  const removeAction = (i: number) => setActions((a) => a.filter((_, idx) => idx !== i));

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const cleanedConditions: AutomationCondition[] = conditions
        .filter((c) => c.field.trim() !== "")
        .map((c) => ({ field: c.field.trim(), op: c.op, value: c.value }));
      await automationsApi.createRule({
        name,
        trigger_event: trigger,
        max_depth: Number(maxDepth) || 5,
        conditions: cleanedConditions,
        actions: actions.map((a) => ({ action_type: a.action_type, config: buildConfig(a) })),
      });
      setDialogOpen(false);
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar la regla");
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (id: string, is_active: boolean) => {
    try {
      await automationsApi.toggleRule(id, is_active);
      setRules((rs) => rs.map((r) => (r.id === id ? { ...r, is_active } : r)));
    } catch {
      // ignore
    }
  };

  const remove = async (id: string) => {
    if (!window.confirm("¿Eliminar esta regla?")) return;
    try {
      await automationsApi.removeRule(id);
      await load();
    } catch {
      // ignore
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6" /> Automatizaciones
          </h1>
          <p className="text-sm text-muted-foreground">Reglas que reaccionan a eventos del CRM</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border overflow-hidden">
            <button
              onClick={() => setView("rules")}
              className={cn("px-3 py-1.5 text-sm", view === "rules" ? "bg-primary text-primary-foreground" : "hover:bg-accent")}
            >
              Reglas
            </button>
            <button
              onClick={() => setView("executions")}
              className={cn("px-3 py-1.5 text-sm", view === "executions" ? "bg-primary text-primary-foreground" : "hover:bg-accent")}
            >
              Ejecuciones
            </button>
          </div>
          <Button onClick={openBuilder}>+ Nueva regla</Button>
        </div>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Cargando...</p>
      ) : view === "rules" ? (
        <div className="space-y-3">
          {rules.length === 0 && <p className="text-muted-foreground">Sin reglas. Crea la primera.</p>}
          {rules.map((r) => (
            <div key={r.id} className="border rounded-lg p-4 flex items-center justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium">{r.name}</p>
                  <Badge variant="outline">{r.trigger_event}</Badge>
                  {!r.is_active && <Badge variant="secondary">inactiva</Badge>}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {r.actions.length} acción(es) · {r.execution_count} ejecuciones
                  {r.last_execution_status ? ` · última: ${r.last_execution_status}` : ""}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Switch checked={r.is_active} onCheckedChange={(v) => void toggle(r.id, v)} aria-label="Activa" />
                <Button variant="ghost" size="sm" onClick={() => void remove(r.id)}>
                  Eliminar
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-foreground text-left">
              <tr>
                <th className="px-3 py-2 font-medium">Regla</th>
                <th className="px-3 py-2 font-medium">Estado</th>
                <th className="px-3 py-2 font-medium">Profundidad</th>
                <th className="px-3 py-2 font-medium">Fecha</th>
                <th className="px-3 py-2 font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {executions.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-muted-foreground">Sin ejecuciones.</td>
                </tr>
              )}
              {executions.map((e) => (
                <tr key={e.id} className="border-t">
                  <td className="px-3 py-2">{e.rule_name ?? e.rule_id}</td>
                  <td className="px-3 py-2">{statusBadge(e.status)}</td>
                  <td className="px-3 py-2">{e.depth}</td>
                  <td className="px-3 py-2">{new Date(e.started_at).toLocaleString()}</td>
                  <td className="px-3 py-2 text-red-600 max-w-xs truncate">{e.error ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Nueva regla</DialogTitle>
            <DialogDescription>Define el disparador, condiciones y acciones.</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-1">
              <Label>Nombre</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej. Seguimiento al ganar" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Evento disparador</Label>
                <select
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm"
                  value={trigger}
                  onChange={(e) => setTrigger(e.target.value)}
                >
                  {EVENT_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label>Profundidad máxima</Label>
                <Input type="number" value={maxDepth} onChange={(e) => setMaxDepth(e.target.value)} min={1} />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Condiciones (AND)</Label>
                <Button type="button" variant="outline" size="sm" onClick={addCondition}>+ condición</Button>
              </div>
              {conditions.map((c, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <Input placeholder="campo (ej. to_stage_id)" value={c.field} onChange={(e) => updateCondition(i, { field: e.target.value })} />
                  <select
                    className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                    value={c.op}
                    onChange={(e) => updateCondition(i, { op: e.target.value as AutomationOperator })}
                  >
                    {OPERATORS.map((o) => (
                      <option key={o} value={o}>{o}</option>
                    ))}
                  </select>
                  <Input placeholder="valor" value={c.value} onChange={(e) => updateCondition(i, { value: e.target.value })} />
                  <Button type="button" variant="ghost" size="sm" onClick={() => removeCondition(i)}>×</Button>
                </div>
              ))}
              {conditions.length === 0 && <p className="text-xs text-muted-foreground">Sin condiciones → siempre se ejecuta.</p>}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Acciones (en orden)</Label>
                <Button type="button" variant="outline" size="sm" onClick={addAction}>+ acción</Button>
              </div>
              {actions.map((a, i) => (
                <div key={i} className="border rounded-md p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <select
                      className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                      value={a.action_type}
                      onChange={(e) => updateAction(i, { action_type: e.target.value })}
                    >
                      {ACTION_TYPES.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <span className="text-xs text-muted-foreground">posición {i + 1}</span>
                    <Button type="button" variant="ghost" size="sm" className="ml-auto" onClick={() => removeAction(i)}>Eliminar</Button>
                  </div>

                  {a.action_type === "create_task" && (
                    <div className="grid grid-cols-2 gap-2">
                      <Input placeholder="Título (puede usar {{event.title}})" value={a.title} onChange={(e) => updateAction(i, { title: e.target.value })} />
                      <select className="h-9 rounded-md border border-input bg-background px-2 text-sm" value={a.priority} onChange={(e) => updateAction(i, { priority: e.target.value })}>
                        {["low", "medium", "high", "urgent"].map((p) => <option key={p} value={p}>{p}</option>)}
                      </select>
                      <Input type="number" placeholder="Desfase en días" value={a.due_offset_days} onChange={(e) => updateAction(i, { due_offset_days: e.target.value })} />
                      <Input placeholder="Asignado a (user id, opcional)" value={a.assigned_user_id} onChange={(e) => updateAction(i, { assigned_user_id: e.target.value })} />
                    </div>
                  )}
                  {a.action_type === "create_activity" && (
                    <div className="grid grid-cols-2 gap-2">
                      <select className="h-9 rounded-md border border-input bg-background px-2 text-sm" value={a.activity_type} onChange={(e) => updateAction(i, { activity_type: e.target.value })}>
                        {["note", "call", "email"].map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                      <Input placeholder="Asunto" value={a.subject} onChange={(e) => updateAction(i, { subject: e.target.value })} />
                    </div>
                  )}
                  {a.action_type === "move_stage" && (
                    <Input placeholder="stage_id destino" value={a.stage_id} onChange={(e) => updateAction(i, { stage_id: e.target.value })} />
                  )}
                  {a.action_type === "update_field" && (
                    <div className="grid grid-cols-2 gap-2">
                      <select className="h-9 rounded-md border border-input bg-background px-2 text-sm" value={a.field} onChange={(e) => updateAction(i, { field: e.target.value })}>
                        {UPDATE_FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
                      </select>
                      <Input placeholder="Valor" value={a.value} onChange={(e) => updateAction(i, { value: e.target.value })} />
                    </div>
                  )}
                </div>
              ))}
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancelar</Button>
            <Button onClick={() => void submit()} disabled={saving || name.trim() === ""}>
              {saving ? "Guardando..." : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
