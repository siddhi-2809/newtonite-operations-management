import React from "react";
import { WorkItemType } from "@/types";
import { Bug, Sparkles, CheckSquare, AlertOctagon } from "lucide-react";

interface TypeBadgeProps {
  type: WorkItemType;
  size?: "sm" | "md";
}

export function TypeBadge({ type, size = "md" }: TypeBadgeProps) {
  const configs: Record<
    WorkItemType,
    { label: string; icon: React.ReactNode; color: string }
  > = {
    BUG: {
      label: "Bug",
      icon: <Bug className="w-3.5 h-3.5 text-rose-400" />,
      color: "text-rose-400",
    },
    FEATURE: {
      label: "Feature",
      icon: <Sparkles className="w-3.5 h-3.5 text-purple-400" />,
      color: "text-purple-400",
    },
    TASK: {
      label: "Task",
      icon: <CheckSquare className="w-3.5 h-3.5 text-blue-400" />,
      color: "text-blue-400",
    },
    INCIDENT: {
      label: "Incident",
      icon: <AlertOctagon className="w-3.5 h-3.5 text-orange-400" />,
      color: "text-orange-400",
    },
  };

  const config = configs[type] || configs.TASK;
  const sizeClasses = size === "sm" ? "text-xs" : "text-xs";

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium ${config.color} ${sizeClasses}`}>
      {config.icon}
      {config.label}
    </span>
  );
}
