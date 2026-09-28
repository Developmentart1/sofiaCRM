import { format, formatDistanceToNow, parseISO, isValid } from "date-fns";
import { es } from "date-fns/locale";

const DEFAULT_CURRENCY = "USD";

export function formatCurrency(
  amount: number | null | undefined,
  currency: string = DEFAULT_CURRENCY
): string {
  if (amount == null) return "—";
  try {
    return new Intl.NumberFormat("es-MX", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString("es-MX")}`;
  }
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("es-MX").format(value);
}

export function formatPercent(value: number | null | undefined, fractionDigits = 1): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = typeof value === "string" ? parseISO(value) : value;
  if (!isValid(date)) return "—";
  return format(date, "dd MMM yyyy", { locale: es });
}

export function formatDateTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = typeof value === "string" ? parseISO(value) : value;
  if (!isValid(date)) return "—";
  return format(date, "dd MMM yyyy, HH:mm", { locale: es });
}

export function formatRelative(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = typeof value === "string" ? parseISO(value) : value;
  if (!isValid(date)) return "—";
  return formatDistanceToNow(date, { addSuffix: true, locale: es });
}

export function formatPhone(phone: string | null | undefined): string {
  if (!phone) return "—";
  return phone;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function fullName(first: string, last: string): string {
  return [first, last].filter(Boolean).join(" ").trim() || "—";
}

export function initials(first: string, last: string): string {
  const f = (first?.[0] ?? "").toUpperCase();
  const l = (last?.[0] ?? "").toUpperCase();
  return `${f}${l}` || "?";
}
