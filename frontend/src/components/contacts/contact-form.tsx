"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { contactSchema, type ContactInput } from "@/lib/utils/validation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FormField } from "@/components/common/form-field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Company, Contact } from "@/lib/types/api";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DuplicateWarning } from "./duplicate-warning";

interface ContactFormProps {
  defaultValues?: Partial<Contact>;
  companies?: Company[];
  onSubmit: (data: ContactInput) => Promise<void> | void;
  onCancel?: () => void;
  submitLabel?: string;
  loading?: boolean;
}

export function ContactForm({ defaultValues, companies = [], onSubmit, onCancel, submitLabel = "Guardar", loading }: ContactFormProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ContactInput>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      first_name: defaultValues?.first_name ?? "",
      last_name: defaultValues?.last_name ?? "",
      email: defaultValues?.email ?? "",
      phone: defaultValues?.phone ?? "",
      job_title: defaultValues?.job_title ?? "",
      company_id: defaultValues?.company_id ?? "",
      status: defaultValues?.status ?? "lead",
      source: defaultValues?.source ?? "",
      tags: defaultValues?.tags ?? [],
      notes: defaultValues?.notes ?? "",
    },
  });

  const [tagInput, setTagInput] = React.useState("");
  const tags = watch("tags") ?? [];
  const status = watch("status");
  const email = watch("email");
  const phone = watch("phone");

  const addTag = () => {
    const t = tagInput.trim();
    if (!t) return;
    if (tags.includes(t)) {
      setTagInput("");
      return;
    }
    setValue("tags", [...tags, t], { shouldValidate: true });
    setTagInput("");
  };
  const removeTag = (t: string) => setValue("tags", tags.filter((x) => x !== t), { shouldValidate: true });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField label="Nombre" htmlFor="first_name" error={errors.first_name?.message} required>
          <Input id="first_name" autoComplete="given-name" aria-invalid={!!errors.first_name} {...register("first_name")} />
        </FormField>
        <FormField label="Apellido" htmlFor="last_name" error={errors.last_name?.message} required>
          <Input id="last_name" autoComplete="family-name" aria-invalid={!!errors.last_name} {...register("last_name")} />
        </FormField>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField label="Email" htmlFor="email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="email" aria-invalid={!!errors.email} {...register("email")} />
        </FormField>
        <FormField label="Teléfono" htmlFor="phone" error={errors.phone?.message}>
          <Input id="phone" type="tel" autoComplete="tel" aria-invalid={!!errors.phone} {...register("phone")} />
        </FormField>
      </div>
      <DuplicateWarning email={email} phone={phone} excludeId={defaultValues?.id} />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField label="Puesto" htmlFor="job_title" error={errors.job_title?.message}>
          <Input id="job_title" aria-invalid={!!errors.job_title} {...register("job_title")} />
        </FormField>
        <FormField label="Empresa" htmlFor="company_id" error={errors.company_id?.message}>
          <Select
            value={watch("company_id") || "none"}
            onValueChange={(v) => setValue("company_id", v === "none" ? "" : v, { shouldValidate: true })}
          >
            <SelectTrigger id="company_id">
              <SelectValue placeholder="Selecciona empresa" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">Sin empresa</SelectItem>
              {companies.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <FormField label="Estado" htmlFor="status" error={errors.status?.message}>
          <Select value={status} onValueChange={(v) => setValue("status", v as ContactInput["status"], { shouldValidate: true })}>
            <SelectTrigger id="status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="lead">Lead</SelectItem>
              <SelectItem value="active">Activo</SelectItem>
              <SelectItem value="customer">Cliente</SelectItem>
              <SelectItem value="inactive">Inactivo</SelectItem>
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Origen" htmlFor="source" error={errors.source?.message}>
          <Input id="source" placeholder="web, referido, evento..." aria-invalid={!!errors.source} {...register("source")} />
        </FormField>
      </div>
      <FormField label="Etiquetas" htmlFor="tag-input">
        <div className="flex flex-wrap items-center gap-2 rounded-md border p-2">
          {tags.map((t) => (
            <Badge key={t} variant="secondary" className="gap-1">
              {t}
              <button type="button" onClick={() => removeTag(t)} aria-label={`Quitar etiqueta ${t}`}>
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          <input
            id="tag-input"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addTag();
              }
            }}
            placeholder="Añadir etiqueta y Enter"
            className="flex-1 min-w-[100px] bg-transparent text-sm outline-none"
          />
        </div>
      </FormField>
      <FormField label="Notas" htmlFor="notes" error={errors.notes?.message}>
        <Textarea id="notes" rows={4} aria-invalid={!!errors.notes} {...register("notes")} />
      </FormField>
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
            Cancelar
          </Button>
        )}
        <Button type="submit" disabled={loading}>
          {loading ? "Guardando..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}
