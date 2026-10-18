import React from "react";
import { WorkItemStatus } from "@/types";
import { CircleDot, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";

interface StatusBadgeProps {
  status: WorkItemStatus;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const configs: Record<
    WorkItemStatus,
    { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    OPEN: {
      label: "Open",
      bg: "bg-sky-500/10",
      text: "text-sky-400",
      border: "border-sky-500/20",
      icon: <CircleDot className="w-3.5 h-3.5" />,
    },
    IN_PROGRESS: {
      label: "In Progress",
      bg: "bg-amber-500/10",
      text: "text-amber-400",
      border: "border-amber-500/20",
      icon: <Clock className="w-3.5 h-3.5 animate-pulse" />,
    },
    BLOCKED: {
      label: "Blocked",
      bg: "bg-rose-500/10",
      text: "text-rose-400",
      border: "border-rose-500/20",
      icon: <AlertTriangle className="w-3.5 h-3.5" />,
    },
    RESOLVED: {
      label: "Resolved",
      bg: "bg-emerald-500/10",
      text: "text-emerald-400",
      border: "border-emerald-500/20",
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    },
  };

  const config = configs[status] || configs.OPEN;
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      {config.icon}
      {config.label}
    </span>
  );
}
