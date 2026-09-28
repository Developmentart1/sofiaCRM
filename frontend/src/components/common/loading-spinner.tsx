import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function LoadingSpinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-4 w-4 animate-spin", className)} aria-label="Cargando" />;
}

export function LoadingPage() {
  return (
    <div className="flex h-[60vh] items-center justify-center">
      <LoadingSpinner className="h-6 w-6" />
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-muted", className)} aria-hidden="true" />;
}
