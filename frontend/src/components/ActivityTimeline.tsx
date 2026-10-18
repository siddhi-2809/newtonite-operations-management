import React from "react";
import { ActivityLog } from "@/types";
import { History, UserCircle, CheckCircle, Edit3, MessageSquare, ArrowRight } from "lucide-react";

interface ActivityTimelineProps {
  activities: ActivityLog[];
}

export function ActivityTimeline({ activities }: ActivityTimelineProps) {
  if (!activities || activities.length === 0) {
    return (
      <div className="py-8 text-center text-slate-500 text-sm">
        No recorded activity yet.
      </div>
    );
  }

  const getActionIcon = (action: string) => {
    if (action.includes("STATUS")) {
      return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    }
    if (action.includes("ASSIGN")) {
      return <UserCircle className="w-4 h-4 text-blue-400" />;
    }
    if (action.includes("COMMENT")) {
      return <MessageSquare className="w-4 h-4 text-purple-400" />;
    }
    return <Edit3 className="w-4 h-4 text-amber-400" />;
  };

  const formatTimestamp = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }).format(date);
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-300 pb-2 border-b border-slate-800">
        <History className="w-4 h-4 text-indigo-400" />
        <span>Audit Trail & Activity Log</span>
      </div>

      <div className="relative pl-6 border-l border-slate-800 space-y-6">
        {activities.map((item) => (
          <div key={item.id} className="relative group">
            {/* Timeline bullet icon */}
            <div className="absolute -left-[31px] top-0.5 p-1 rounded-full bg-slate-900 border border-slate-700">
              {getActionIcon(item.action)}
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-slate-200">
                  {item.actor ? item.actor.full_name : `User #${item.actor_id}`}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/50">
                  {item.action}
                </span>
                <span className="text-xs text-slate-500 ml-auto">
                  {formatTimestamp(item.timestamp)}
                </span>
              </div>

              {/* Show transition if previous and new value exist */}
              {item.previous_value !== null && item.new_value !== null ? (
                <div className="flex items-center gap-2 text-xs text-slate-300 mt-1 bg-slate-900/60 p-2 rounded-lg border border-slate-800">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 line-through">
                    {item.previous_value || "None"}
                  </span>
                  <ArrowRight className="w-3 h-3 text-slate-500" />
                  <span className="px-2 py-0.5 rounded bg-indigo-950/60 border border-indigo-500/30 text-indigo-300 font-medium">
                    {item.new_value}
                  </span>
                </div>
              ) : item.new_value ? (
                <p className="text-xs text-slate-400 mt-1 bg-slate-900/40 p-2 rounded-lg border border-slate-800/80">
                  {item.new_value}
                </p>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
