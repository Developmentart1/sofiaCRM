"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { taskSchema, type TaskInput } from "@/lib/utils/validation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FormField } from "@/components/common/form-field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface TaskFormProps {
  defaultValues?: Partial<TaskInput>;
  onSubmit: (data: TaskInput) => Promise<void> | void;
  onCancel?: () => void;
  submitLabel?: string;
  loading?: boolean;
}

export function TaskForm({ defaultValues, onSubmit, onCancel, submitLabel = "Crear tarea", loading }: TaskFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<TaskInput>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: defaultValues?.title ?? "",
      description: defaultValues?.description ?? "",
      status: defaultValues?.status ?? "pending",
      priority: defaultValues?.priority ?? "medium",
      due_date: defaultValues?.due_date ?? "",
      contact_id: defaultValues?.contact_id ?? "",
      opportunity_id: defaultValues?.opportunity_id ?? "",
      company_id: defaultValues?.company_id ?? "",
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
      <FormField label="Título" htmlFor="title" error={errors.title?.message} required>
        <Input id="title" aria-invalid={!!errors.title} {...register("title")} />
      </FormField>
      <FormField label="Descripción" htmlFor="description" error={errors.description?.message}>
        <Textarea id="description" rows={3} {...register("description")} />
      </FormField>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <FormField label="Estado" htmlFor="status">
          <Select value={watch("status")} onValueChange={(v) => setValue("status", v as TaskInput["status"])}>
            <SelectTrigger id="status"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="pending">Pendiente</SelectItem>
              <SelectItem value="in_progress">En curso</SelectItem>
              <SelectItem value="completed">Completada</SelectItem>
              <SelectItem value="cancelled">Cancelada</SelectItem>
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Prioridad" htmlFor="priority">
          <Select value={watch("priority")} onValueChange={(v) => setValue("priority", v as TaskInput["priority"])}>
            <SelectTrigger id="priority"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="low">Baja</SelectItem>
              <SelectItem value="medium">Media</SelectItem>
              <SelectItem value="high">Alta</SelectItem>
              <SelectItem value="urgent">Urgente</SelectItem>
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Vencimiento" htmlFor="due_date" error={errors.due_date?.message}>
          <Input id="due_date" type="datetime-local" {...register("due_date")} />
        </FormField>
      </div>
      <div className="flex justify-end gap-2">
        {onCancel && <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>Cancelar</Button>}
        <Button type="submit" disabled={loading}>{loading ? "Guardando..." : submitLabel}</Button>
      </div>
    </form>
  );
}
