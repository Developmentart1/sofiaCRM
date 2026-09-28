"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { activitySchema, type ActivityInput } from "@/lib/utils/validation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FormField } from "@/components/common/form-field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface ActivityFormProps {
  defaultValues?: Partial<ActivityInput>;
  onSubmit: (data: ActivityInput) => Promise<void> | void;
  onCancel?: () => void;
  submitLabel?: string;
  loading?: boolean;
}

export function ActivityForm({ defaultValues, onSubmit, onCancel, submitLabel = "Registrar", loading }: ActivityFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ActivityInput>({
    resolver: zodResolver(activitySchema),
    defaultValues: {
      type: defaultValues?.type ?? "note",
      subject: defaultValues?.subject ?? "",
      body: defaultValues?.body ?? "",
      occurred_at: defaultValues?.occurred_at ?? new Date().toISOString().slice(0, 16),
      duration_minutes: defaultValues?.duration_minutes,
      contact_id: defaultValues?.contact_id ?? "",
      opportunity_id: defaultValues?.opportunity_id ?? "",
      company_id: defaultValues?.company_id ?? "",
    },
  });

  const type = watch("type");
  const showDuration = type === "call" || type === "meeting";

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField label="Tipo" htmlFor="type" required>
          <Select value={type} onValueChange={(v) => setValue("type", v as ActivityInput["type"], { shouldValidate: true })}>
            <SelectTrigger id="type"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="note">Nota</SelectItem>
              <SelectItem value="call">Llamada</SelectItem>
              <SelectItem value="email">Email</SelectItem>
              <SelectItem value="meeting">Reunión</SelectItem>
              <SelectItem value="sms">SMS</SelectItem>
              <SelectItem value="whatsapp">WhatsApp</SelectItem>
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Fecha" htmlFor="occurred_at" error={errors.occurred_at?.message}>
          <Input id="occurred_at" type="datetime-local" {...register("occurred_at")} />
        </FormField>
      </div>
      <FormField label="Asunto" htmlFor="subject" error={errors.subject?.message} required>
        <Input id="subject" aria-invalid={!!errors.subject} {...register("subject")} />
      </FormField>
      {showDuration && (
        <FormField label="Duración (minutos)" htmlFor="duration_minutes" error={errors.duration_minutes?.message}>
          <Input id="duration_minutes" type="number" min={0} {...register("duration_minutes", { valueAsNumber: true })} />
        </FormField>
      )}
      <FormField label="Notas" htmlFor="body" error={errors.body?.message}>
        <Textarea id="body" rows={4} {...register("body")} />
      </FormField>
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>Cancelar</Button>
        )}
        <Button type="submit" disabled={loading}>{loading ? "Guardando..." : submitLabel}</Button>
      </div>
    </form>
  );
}
