import * as React from "react";
import { type LucideIcon, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils/cn";

interface KpiCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  change?: number;
  changeLabel?: string;
  className?: string;
  iconClassName?: string;
}

export function KpiCard({ label, value, icon: Icon, change, changeLabel, className, iconClassName }: KpiCardProps) {
  const positive = (change ?? 0) >= 0;
  return (
    <Card className={className}>
      <CardContent className="flex items-start gap-3 p-4">
        <div className={cn("flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary", iconClassName)}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-1 text-2xl font-semibold tracking-tight">{value}</p>
          {change !== undefined && (
            <div className={cn("mt-1 inline-flex items-center gap-1 text-xs", positive ? "text-emerald-600" : "text-rose-600")}>
              {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              <span>
                {positive ? "+" : ""}
                {change.toFixed(1)}%
              </span>
              {changeLabel && <span className="text-muted-foreground">vs {changeLabel}</span>}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
