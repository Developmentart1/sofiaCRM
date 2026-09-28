"use client";

import * as React from "react";
import { Bell, Search, Sun, Moon, Plus } from "lucide-react";
import { useTheme } from "next-themes";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/lib/hooks/use-auth";
import { initials } from "@/lib/utils/format";
import Link from "next/link";

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);
  if (!mounted) {
    return <Button variant="ghost" size="icon" aria-label="Cambiar tema" className="h-9 w-9" />;
  }
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Cambiar tema"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      {resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}

export function Topbar() {
  const { user } = useAuth();

  return (
    <header className="flex h-14 items-center gap-3 border-b bg-card px-4">
      <div className="relative max-w-md flex-1">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
        <Input placeholder="Buscar contactos, empresas, oportunidades..." className="pl-8" aria-label="Búsqueda global" />
      </div>
      <div className="ml-auto flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Crear nuevo">
              <Plus className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Crear</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/contacts/new">Nuevo contacto</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/companies/new">Nueva empresa</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/opportunities/new">Nueva oportunidad</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/tasks">Nueva tarea</Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <ThemeToggle />
        <Button variant="ghost" size="icon" aria-label="Notificaciones">
          <Bell className="h-4 w-4" />
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label="Menú de usuario">
              <Avatar className="h-8 w-8">
                <AvatarFallback>{user ? initials(user.full_name.split(" ")[0] ?? "", user.full_name.split(" ")[1] ?? "") : "?"}</AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span className="text-sm font-medium">{user?.full_name ?? "Usuario"}</span>
                <span className="text-xs text-muted-foreground">{user?.email}</span>
                <span className="mt-1 text-xs text-muted-foreground">CRM Splash</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings">Configuración</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings/users">Equipo</Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
