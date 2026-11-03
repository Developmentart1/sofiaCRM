"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Building2,
  Target,
  GitBranch,
  ListTodo,
  Activity,
  FileText,
  BarChart3,
  Settings,
  ChevronsLeft,
  ChevronsRight,
  LogOut,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuth } from "@/lib/hooks/use-auth";
import { hasPermission } from "@/lib/types/domain";
import { APP_NAME } from "@/lib/config";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  permission?: Parameters<typeof hasPermission>[1];
}

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/contacts", label: "Contactos", icon: Users, permission: "contacts:read" },
  { href: "/companies", label: "Empresas", icon: Building2, permission: "companies:read" },
  { href: "/opportunities", label: "Oportunidades", icon: Target, permission: "opportunities:read" },
  { href: "/pipelines", label: "Pipelines", icon: GitBranch, permission: "pipelines:read" },
  { href: "/tasks", label: "Tareas", icon: ListTodo },
  { href: "/activities", label: "Actividades", icon: Activity, permission: "activities:read" },
  { href: "/automations", label: "Automatizaciones", icon: Zap, permission: "automations:read" },
  { href: "/documents", label: "Documentos", icon: FileText, permission: "documents:read" },
  { href: "/reports", label: "Reportes", icon: BarChart3, permission: "reports:read" },
  { href: "/settings", label: "Configuración", icon: Settings, permission: "settings:read" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = React.useState(false);

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          "hidden md:flex h-screen flex-col border-r bg-secondary transition-[width] duration-200",
          collapsed ? "w-16" : "w-60"
        )}
        aria-label="Navegación principal"
      >
        <div className="flex h-16 items-center gap-3 border-b border-foreground/15 px-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center bg-primary text-primary-foreground font-black">
            C
          </div>
          {!collapsed && <span className="truncate text-sm font-semibold">{APP_NAME}</span>}
        </div>

        <nav className="flex-1 overflow-y-auto p-2">
          <ul className="space-y-0.5">
            {NAV.map((item) => {
              if (item.permission && !hasPermission(user?.role, item.permission)) return null;
              const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
              const link = (
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 border-l-2 border-transparent px-3 py-2.5 text-sm transition-colors",
                    active
                      ? "border-primary bg-white text-foreground font-bold"
                      : "text-muted-foreground hover:border-foreground/20 hover:bg-white/70 hover:text-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );
              return (
                <li key={item.href}>
                  {collapsed ? (
                    <Tooltip>
                      <TooltipTrigger asChild>{link}</TooltipTrigger>
                      <TooltipContent side="right">{item.label}</TooltipContent>
                    </Tooltip>
                  ) : (
                    link
                  )}
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t p-2">
          <div className={cn("flex items-center gap-2", collapsed ? "justify-center" : "justify-between")}>
            {!collapsed && (
              <button
                onClick={() => void logout()}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
                aria-label="Cerrar sesión"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Salir</span>
              </button>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setCollapsed((c) => !c)}
              aria-label={collapsed ? "Expandir menú" : "Colapsar menú"}
              className="h-7 w-7"
            >
              {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
}
