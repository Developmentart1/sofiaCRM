import type { UserRole } from "./api";

export type Permission =
  | "contacts:read"
  | "contacts:write"
  | "contacts:delete"
  | "companies:read"
  | "companies:write"
  | "companies:delete"
  | "opportunities:read"
  | "opportunities:write"
  | "opportunities:delete"
  | "pipelines:read"
  | "pipelines:write"
  | "pipelines:delete"
  | "tasks:read"
  | "tasks:write"
  | "tasks:delete"
  | "activities:read"
  | "activities:write"
  | "documents:read"
  | "documents:write"
  | "documents:delete"
  | "reports:read"
  | "users:read"
  | "users:write"
  | "settings:read"
  | "settings:write"
  | "automations:read"
  | "automations:write";

const ROLE_PERMISSIONS: Record<UserRole, ReadonlySet<Permission>> = {
  admin: new Set<Permission>([
    "contacts:read", "contacts:write", "contacts:delete",
    "companies:read", "companies:write", "companies:delete",
    "opportunities:read", "opportunities:write", "opportunities:delete",
    "pipelines:read", "pipelines:write", "pipelines:delete",
    "tasks:read", "tasks:write", "tasks:delete",
    "activities:read", "activities:write",
    "documents:read", "documents:write", "documents:delete",
    "reports:read",
    "users:read", "users:write",
    "settings:read", "settings:write",
    "automations:read", "automations:write",
  ]),
  director: new Set<Permission>([
    "contacts:read", "contacts:write", "contacts:delete",
    "companies:read", "companies:write", "companies:delete",
    "opportunities:read", "opportunities:write", "opportunities:delete",
    "pipelines:read", "pipelines:write",
    "tasks:read", "tasks:write", "tasks:delete",
    "activities:read", "activities:write",
    "documents:read", "documents:write", "documents:delete",
    "reports:read",
    "users:read",
    "settings:read",
    "automations:read", "automations:write",
  ]),
  gerente: new Set<Permission>([
    "contacts:read", "contacts:write",
    "companies:read", "companies:write",
    "opportunities:read", "opportunities:write",
    "pipelines:read",
    "tasks:read", "tasks:write",
    "activities:read", "activities:write",
    "documents:read", "documents:write",
    "reports:read",
  ]),
  asesor: new Set<Permission>([
    "contacts:read", "contacts:write",
    "companies:read", "companies:write",
    "opportunities:read", "opportunities:write",
    "pipelines:read",
    "tasks:read", "tasks:write",
    "activities:read", "activities:write",
    "documents:read", "documents:write",
    "reports:read",
  ]),
  operaciones: new Set<Permission>([
    "contacts:read",
    "companies:read",
    "opportunities:read",
    "pipelines:read",
    "tasks:read",
    "activities:read",
    "documents:read",
    "reports:read",
  ]),
};

export function hasPermission(role: UserRole | undefined, permission: Permission): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role].has(permission);
}
