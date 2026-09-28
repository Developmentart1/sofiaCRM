import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Email inválido"),
  password: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
  organization_slug: z.string().min(2, "Slug de organización requerido"),
});

export const signupSchema = z.object({
  organization_name: z.string().min(2, "Nombre de la organización requerido"),
  full_name: z.string().min(2, "Tu nombre es requerido"),
  email: z.string().email("Email inválido"),
  password: z.string().min(8, "La contraseña debe tener al menos 8 caracteres"),
});

export const contactSchema = z.object({
  first_name: z.string().min(1, "Nombre requerido"),
  last_name: z.string().min(1, "Apellido requerido"),
  email: z.string().email("Email inválido").optional().or(z.literal("")),
  phone: z.string().optional().or(z.literal("")),
  job_title: z.string().optional().or(z.literal("")),
  company_id: z.string().optional().or(z.literal("")),
  status: z.enum(["active", "inactive", "lead", "customer"]).default("lead"),
  source: z.string().optional().or(z.literal("")),
  tags: z.array(z.string()).default([]),
  notes: z.string().optional().or(z.literal("")),
});

export const companySchema = z.object({
  name: z.string().min(1, "Nombre requerido"),
  domain: z.string().optional().or(z.literal("")),
  industry: z.string().optional().or(z.literal("")),
  size: z.string().optional().or(z.literal("")),
  revenue: z.coerce.number().nonnegative().optional().or(z.nan()),
  phone: z.string().optional().or(z.literal("")),
  address: z.string().optional().or(z.literal("")),
  city: z.string().optional().or(z.literal("")),
  country: z.string().optional().or(z.literal("")),
  website: z.string().url("URL inválida").optional().or(z.literal("")),
});

export const opportunitySchema = z.object({
  name: z.string().min(1, "Nombre requerido"),
  estimated_value: z.coerce.number().nonnegative("Monto debe ser positivo"),
  currency: z.string().default("MXN"),
  pipeline_id: z.string().min(1, "Pipeline requerido"),
  stage_id: z.string().min(1, "Etapa requerida"),
  expected_close_date: z.string().optional().or(z.literal("")),
  contact_id: z.string().optional().or(z.literal("")),
  company_id: z.string().optional().or(z.literal("")),
  description: z.string().optional().or(z.literal("")),
  priority: z.string().optional(),
  source_id: z.string().optional().or(z.literal("")),
});

export const stageTransitionSchema = z.object({
  stage_id: z.string().min(1, "Selecciona una etapa"),
  lost_reason_id: z.string().optional().or(z.literal("")),
  lost_notes: z.string().optional().or(z.literal("")),
});

export const taskSchema = z.object({
  title: z.string().min(1, "Título requerido"),
  description: z.string().optional().or(z.literal("")),
  status: z.enum(["pending", "in_progress", "completed", "cancelled"]).default("pending"),
  priority: z.enum(["low", "medium", "high", "urgent"]).default("medium"),
  due_date: z.string().optional().or(z.literal("")),
  contact_id: z.string().optional().or(z.literal("")),
  opportunity_id: z.string().optional().or(z.literal("")),
  company_id: z.string().optional().or(z.literal("")),
});

export const activitySchema = z.object({
  type: z.enum(["note", "call", "email", "meeting", "sms", "whatsapp"]),
  subject: z.string().min(1, "Asunto requerido"),
  body: z.string().optional().or(z.literal("")),
  occurred_at: z.string().optional().or(z.literal("")),
  duration_minutes: z.coerce.number().nonnegative().optional().or(z.nan()),
  contact_id: z.string().optional().or(z.literal("")),
  opportunity_id: z.string().optional().or(z.literal("")),
  company_id: z.string().optional().or(z.literal("")),
});

export const pipelineSchema = z.object({
  name: z.string().min(1, "Nombre requerido"),
  description: z.string().optional().or(z.literal("")),
  is_default: z.boolean().default(false),
});

export const stageSchema = z.object({
  name: z.string().min(1, "Nombre requerido"),
  order: z.coerce.number().int().nonnegative(),
  probability: z.coerce.number().min(0).max(100),
  color: z.string().default("#6366f1"),
  is_won: z.boolean().default(false),
  is_lost: z.boolean().default(false),
});

export type LoginInput = z.infer<typeof loginSchema>;
export type SignupInput = z.infer<typeof signupSchema>;
export type ContactInput = z.infer<typeof contactSchema>;
export type CompanyInput = z.infer<typeof companySchema>;
export type OpportunityInput = z.infer<typeof opportunitySchema>;
export type StageTransitionInput = z.infer<typeof stageTransitionSchema>;
export type TaskInput = z.infer<typeof taskSchema>;
export type ActivityInput = z.infer<typeof activitySchema>;
export type PipelineInput = z.infer<typeof pipelineSchema>;
export type StageInput = z.infer<typeof stageSchema>;
