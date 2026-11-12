// API types — espejo de los schemas Pydantic del backend

export type UUID = string;
export type ISODateString = string;
export type ISODateTimeString = string;

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail?: string;
  code?: string;
  field?: string;
  error?: { code?: string; message?: string; details?: unknown };
}

export type UserRole = "admin" | "director" | "gerente" | "asesor" | "operaciones";

export interface User {
  id: UUID;
  email: string;
  full_name: string;
  role: UserRole;
  organization_id: UUID;
  is_active: boolean;
  avatar_url?: string | null;
  created_at: ISODateTimeString;
  last_login_at?: ISODateTimeString | null;
}

export interface Organization {
  id: UUID;
  name: string;
  slug: string;
  plan: "free" | "starter" | "pro" | "enterprise";
  created_at: ISODateTimeString;
}

export interface AuthSession {
  user: User;
  organization: Organization;
  expires_at: ISODateTimeString;
}

export interface LoginPayload {
  email: string;
  password: string;
  organization_slug: string;
}

export interface SignupPayload {
  organization_name: string;
  email: string;
  password: string;
  full_name: string;
}

export type ContactStatus = "active" | "inactive" | "lead" | "customer";

export interface Contact {
  id: UUID;
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  job_title?: string | null;
  company_id?: UUID | null;
  company_name?: string | null;
  status: ContactStatus;
  source?: string | null;
  tags: string[];
  owner_id?: UUID | null;
  owner_name?: string | null;
  custom_fields: Record<string, string | number | boolean | null>;
  notes?: string | null;
  created_at: ISODateTimeString;
  updated_at: ISODateTimeString;
}

export interface ContactCreate {
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  job_title?: string | null;
  company_id?: UUID | null;
  status?: ContactStatus;
  source?: string | null;
  tags?: string[];
  owner_id?: UUID | null;
  custom_fields?: Record<string, string | number | boolean | null>;
  notes?: string | null;
}

export interface ContactFilters {
  [key: string]: unknown;
  search?: string;
  status?: ContactStatus;
  company_id?: UUID;
  owner_id?: UUID;
  tag?: string;
  page?: number;
  page_size?: number;
  sort_by?: "name" | "created_at" | "updated_at" | "last_contacted_at";
  sort_dir?: "asc" | "desc";
}

export interface Company {
  id: UUID;
  name: string;
  domain?: string | null;
  industry?: string | null;
  size?: string | null;
  revenue?: number | null;
  phone?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  website?: string | null;
  owner_id?: UUID | null;
  owner_name?: string | null;
  contact_count: number;
  created_at: ISODateTimeString;
  updated_at: ISODateTimeString;
}

export interface CompanyCreate {
  name: string;
  domain?: string | null;
  industry?: string | null;
  size?: string | null;
  revenue?: number | null;
  phone?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  website?: string | null;
  owner_id?: UUID | null;
}

export interface Pipeline {
  id: UUID;
  name: string;
  description?: string | null;
  is_default: boolean;
  stage_count: number;
  created_at: ISODateTimeString;
  updated_at: ISODateTimeString;
}

export interface PipelineStage {
  id: UUID;
  pipeline_id: UUID;
  name: string;
  order: number;
  probability: number;
  color: string;
  is_won: boolean;
  is_lost: boolean;
  opportunity_count?: number;
}

export type OpportunityStatus = "open" | "won" | "lost";

export interface Opportunity {
  id: UUID;
  organization_id: string;
  name: string;
  description?: string | null;
  estimated_value: number;
  weighted_value: number;
  probability: number;
  priority: string;
  currency: string;
  status: OpportunityStatus;
  expected_close_date?: string | null;
  closed_at?: string | null;
  won_value?: number | null;
  pipeline_id: string;
  stage_id: string;
  contact_id?: string | null;
  company_id?: string | null;
  source_id?: string | null;
  lost_reason_id?: string | null;
  lost_notes?: string | null;
  last_activity_at?: string | null;
  next_activity_at?: string | null;
  entered_stage_at?: string | null;
  assigned_user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpportunityCreate {
  name: string;
  estimated_value: number;
  currency?: string;
  pipeline_id: UUID;
  stage_id: UUID;
  expected_close_date?: ISODateString | null;
  contact_id?: UUID | null;
  company_id?: UUID | null;
  owner_id?: UUID | null;
  description?: string | null;
  priority?: string;
  source_id?: UUID | null;
}

export interface OpportunityFilters {
  [key: string]: unknown;
  search?: string;
  status?: OpportunityStatus;
  pipeline_id?: UUID;
  stage_id?: UUID;
  owner_id?: UUID;
  contact_id?: UUID;
  company_id?: UUID;
  min_amount?: number;
  max_amount?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  view?: "all" | "mine" | "stuck";
}

export interface StageTransition {
  stage_id: UUID;
  lost_reason_id?: UUID | null;
  lost_notes?: string | null;
}

export type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled" | "overdue";
export type TaskPriority = "low" | "medium" | "high" | "urgent";

export interface Task {
  id: UUID;
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date?: ISODateTimeString | null;
  completed_at?: ISODateTimeString | null;
  contact_id?: UUID | null;
  contact_name?: string | null;
  opportunity_id?: UUID | null;
  opportunity_name?: string | null;
  company_id?: UUID | null;
  company_name?: string | null;
  owner_id: UUID;
  owner_name?: string | null;
  created_by_id?: UUID | null;
  created_at: ISODateTimeString;
  updated_at: ISODateTimeString;
}

export interface TaskCreate {
  title: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: TaskPriority;
  due_date?: ISODateTimeString | null;
  contact_id?: UUID | null;
  opportunity_id?: UUID | null;
  company_id?: UUID | null;
  owner_id?: UUID;
}

export interface TaskFilters {
  [key: string]: unknown;
  search?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  owner_id?: UUID;
  contact_id?: UUID;
  opportunity_id?: UUID;
  company_id?: UUID;
  due_before?: ISODateTimeString;
  due_after?: ISODateTimeString;
  view?: "all" | "mine" | "today" | "overdue" | "upcoming";
  page?: number;
  page_size?: number;
}

export interface CompanyFilters {
  [key: string]: unknown;
}
export interface ActivityFilters {
  [key: string]: unknown;
}
export interface DocumentFilters {
  [key: string]: unknown;
}

export type ActivityType =
  | "note"
  | "call"
  | "email"
  | "meeting"
  | "task_completed"
  | "stage_change"
  | "created"
  | "updated"
  | "sms"
  | "whatsapp";

export interface Activity {
  id: UUID;
  type: ActivityType;
  subject: string;
  body?: string | null;
  occurred_at: ISODateTimeString;
  duration_minutes?: number | null;
  contact_id?: UUID | null;
  contact_name?: string | null;
  opportunity_id?: UUID | null;
  opportunity_name?: string | null;
  company_id?: UUID | null;
  company_name?: string | null;
  task_id?: UUID | null;
  user_id: UUID;
  user_name?: string | null;
  metadata?: Record<string, string | number | boolean | null>;
  created_at: ISODateTimeString;
}

export interface ActivityCreate {
  type: ActivityType;
  subject: string;
  body?: string | null;
  occurred_at?: ISODateTimeString;
  duration_minutes?: number | null;
  contact_id?: UUID | null;
  opportunity_id?: UUID | null;
  company_id?: UUID | null;
  task_id?: UUID | null;
}

export interface Document {
  id: UUID;
  name: string;
  mime_type: string;
  size: number;
  url: string;
  contact_id?: UUID | null;
  contact_name?: string | null;
  opportunity_id?: UUID | null;
  opportunity_name?: string | null;
  company_id?: UUID | null;
  company_name?: string | null;
  uploaded_by_id: UUID;
  uploaded_by_name?: string | null;
  folder?: string | null;
  created_at: ISODateTimeString;
}

export interface DashboardKPIs {
  total_contacts: number;
  total_companies: number;
  total_opportunities: number;
  open_opportunities_value: number;
  won_opportunities_value: number;
  won_opportunities_count: number;
  lost_opportunities_count: number;
  conversion_rate: number;
  average_deal_size: number;
  pipeline_velocity: number;
  overdue_tasks: number;
  tasks_due_today: number;
  contacts_added_this_month: number;
  opportunities_won_this_month: number;
}

export interface UserPerformance {
  user_id: UUID;
  user_name: string;
  avatar_url?: string | null;
  opportunities_won: number;
  opportunities_won_value: number;
  opportunities_open: number;
  activities_logged: number;
  tasks_completed: number;
}

export interface ReportSummary {
  total_revenue: number;
  revenue_by_pipeline: Array<{
    pipeline_id: UUID;
    pipeline_name: string;
    revenue: number;
  }>;
  revenue_by_owner: Array<{
    user_id: UUID;
    user_name: string;
    revenue: number;
  }>;
  conversion_by_stage: Array<{
    stage_id: UUID;
    stage_name: string;
    count: number;
    conversion_rate: number;
  }>;
  period_start: ISODateString;
  period_end: ISODateString;
}

export interface AutomationRule {
  id: UUID;
  name: string;
  description?: string | null;
  trigger_type: string;
  trigger_config: Record<string, string | number | boolean | null>;
  actions: Array<{
    type: string;
    config: Record<string, string | number | boolean | null>;
  }>;
  is_active: boolean;
  created_at: ISODateTimeString;
  updated_at: ISODateTimeString;
}

export interface AuditLog {
  id: UUID;
  user_id: UUID;
  user_name?: string | null;
  action: string;
  resource_type: string;
  resource_id?: UUID | null;
  changes?: Record<string, unknown> | null;
  created_at: ISODateTimeString;
  ip_address?: string | null;
}

export type AutomationOperator = "eq" | "neq" | "contains" | "gt" | "lt";

export interface AutomationCondition {
  field: string;
  op: AutomationOperator;
  value: string | number | boolean | null;
}

export interface AutomationActionSpec {
  action_type: string;
  config: Record<string, unknown>;
}

export interface AutomationAction {
  id: UUID;
  action_type: string;
  config: Record<string, unknown>;
  position: number;
}

export interface AutomationRuleRead {
  id: UUID;
  name: string;
  description?: string | null;
  trigger_event: string;
  is_active: boolean;
  max_depth: number;
  conditions: AutomationCondition[];
  actions: AutomationAction[];
  execution_count: number;
  last_execution_status?: string | null;
  created_at: ISODateTimeString;
  updated_at: ISODateTimeString;
}

export interface AutomationRuleCreate {
  name: string;
  description?: string | null;
  trigger_event: string;
  is_active?: boolean;
  max_depth?: number;
  conditions?: AutomationCondition[];
  actions: AutomationActionSpec[];
}

export interface AutomationExecution {
  id: UUID;
  rule_id: UUID;
  rule_name?: string | null;
  trigger_event_id: string;
  status: string;
  depth: number;
  result?: Record<string, unknown> | null;
  error?: string | null;
  started_at: ISODateTimeString;
  finished_at?: ISODateTimeString | null;
}

export interface AutomationTestResult {
  matched: boolean;
  status: string;
  reason?: string | null;
  actions: Array<{
    action_type: string;
    position: number;
    ok: boolean;
    result?: Record<string, unknown> | null;
    error?: string | null;
  }>;
  error?: string | null;
}
