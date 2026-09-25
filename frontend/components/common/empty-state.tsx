import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  body?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-surface-2/50 px-6 py-10 text-center",
        className,
      )}
    >
      {Icon && (
        <div className="flex size-11 items-center justify-center rounded-full bg-cyan-soft text-brand-cyan">
          <Icon className="size-5" />
        </div>
      )}
      <div className="space-y-1">
        <p className="font-display font-semibold text-text">{title}</p>
        {body && <p className="text-sm text-muted max-w-sm">{body}</p>}
      </div>
      {action}
    </div>
  );
}
