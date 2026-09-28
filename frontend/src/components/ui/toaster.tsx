"use client";

import * as React from "react";
import { cn } from "@/lib/utils/cn";
import { useToast } from "@/lib/hooks/use-toast";
import { X } from "lucide-react";

export function Toaster() {
  const { toasts, dismiss } = useToast();
  return (
    <div className="pointer-events-none fixed top-0 z-[100] flex w-full flex-col items-end gap-2 p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:items-end">
      {toasts.map((t: { id: string; variant?: "default" | "success" | "destructive" | "warning"; title?: string; description?: string }) => {
        const variantClass =
          t.variant === "destructive"
            ? "border-destructive/50 bg-destructive text-destructive-foreground"
            : t.variant === "success"
              ? "border-emerald-500/40 bg-emerald-500/10 text-foreground"
              : t.variant === "warning"
                ? "border-amber-500/40 bg-amber-500/10 text-foreground"
                : "border bg-background text-foreground";
        return (
          <div
            key={t.id}
            role="status"
            aria-live="polite"
            className={cn(
              "pointer-events-auto relative flex w-full max-w-sm items-start gap-3 rounded-md border p-4 shadow-lg",
              variantClass
            )}
          >
            <div className="flex-1">
              {t.title && <div className="text-sm font-semibold">{t.title}</div>}
              {t.description && (
                <div className="mt-0.5 text-sm opacity-90">{t.description}</div>
              )}
            </div>
            <button
              onClick={() => dismiss(t.id)}
              className="rounded-md p-1 opacity-60 transition-opacity hover:opacity-100"
              aria-label="Cerrar notificación"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
