import { format, formatDistanceToNow } from "date-fns";

/** Format a number as Indian Rupees, e.g. ₹12,34,567 */
export function formatCurrency(value: number, opts?: { compact?: boolean }): string {
  if (opts?.compact) {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

export function formatDate(value: string | number | Date, pattern = "d MMM yyyy"): string {
  return format(new Date(value), pattern);
}

export function formatDateTime(value: string | number | Date): string {
  return format(new Date(value), "d MMM yyyy, h:mm a");
}

export function formatRelative(value: string | number | Date): string {
  return formatDistanceToNow(new Date(value), { addSuffix: true });
}

export function truncateMiddle(value: string, front = 6, back = 4): string {
  if (value.length <= front + back + 3) return value;
  return `${value.slice(0, front)}…${value.slice(-back)}`;
}

export function etherscanTxUrl(base: string, hash: string): string {
  return `${base.replace(/\/$/, "")}/tx/${hash}`;
}

export function etherscanAddressUrl(base: string, address: string): string {
  return `${base.replace(/\/$/, "")}/address/${address}`;
}
