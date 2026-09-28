import * as React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ message = "Algo salió mal", onRetry, className }: ErrorStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 p-10 text-center", className)}>
      <AlertTriangle className="mb-3 h-6 w-6 text-destructive" aria-hidden="true" />
      <p className="text-sm text-destructive">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="outline" size="sm" className="mt-4">
          <RefreshCw className="mr-2 h-4 w-4" /> Reintentar
        </Button>
      )}
    </div>
  );
}
