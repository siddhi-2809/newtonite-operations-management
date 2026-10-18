import React from "react";
import { WorkItemPriority } from "@/types";
import { Flame, ArrowUp, ArrowRight, ArrowDown } from "lucide-react";

interface PriorityBadgeProps {
  priority: WorkItemPriority;
  size?: "sm" | "md";
}

export function PriorityBadge({ priority, size = "md" }: PriorityBadgeProps) {
  const configs: Record<
    WorkItemPriority,
    { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    LOW: {
      label: "Low",
      bg: "bg-slate-500/10",
      text: "text-slate-400",
      border: "border-slate-500/20",
      icon: <ArrowDown className="w-3.5 h-3.5" />,
    },
    MEDIUM: {
      label: "Medium",
      bg: "bg-blue-500/10",
      text: "text-blue-400",
      border: "border-blue-500/20",
      icon: <ArrowRight className="w-3.5 h-3.5" />,
    },
    HIGH: {
      label: "High",
      bg: "bg-amber-500/10",
      text: "text-amber-400",
      border: "border-amber-500/20",
      icon: <ArrowUp className="w-3.5 h-3.5" />,
    },
    CRITICAL: {
      label: "Critical",
      bg: "bg-red-500/15",
      text: "text-red-400 font-semibold",
      border: "border-red-500/30",
      icon: <Flame className="w-3.5 h-3.5 text-red-500" />,
    },
  };

  const config = configs[priority] || configs.LOW;
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      {config.icon}
      {config.label}
    </span>
  );
}
