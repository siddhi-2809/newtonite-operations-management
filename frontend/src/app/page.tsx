"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { fetchApi } from "@/lib/api";
import { DashboardStats } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { PriorityBadge } from "@/components/PriorityBadge";
import { ActivityTimeline } from "@/components/ActivityTimeline";
import {
  Layers,
  Clock,
  Flame,
  UserCheck,
  AlertTriangle,
  ArrowRight,
  PlusCircle,
  RefreshCw,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApi<DashboardStats>("/api/dashboard/stats");
      setStats(data);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push("/login");
      } else {
        loadStats();
      }
    }
  }, [user, authLoading, router]);

  if (authLoading || (!user && loading)) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-400">Loading operations dashboard...</p>
        </div>
      </div>
    );
  }

  const statCards = [
    {
      label: "Total Work Items",
      value: stats?.total_work_items ?? 0,
      icon: <Layers className="w-5 h-5 text-indigo-400" />,
      bg: "bg-indigo-500/10 border-indigo-500/20",
      description: "Across permitted teams",
      href: "/work-items",
    },
    {
      label: "Open & In Progress",
      value: stats?.open_and_in_progress ?? 0,
      icon: <Clock className="w-5 h-5 text-amber-400" />,
      bg: "bg-amber-500/10 border-amber-500/20",
      description: "Active execution pipeline",
      href: "/work-items?status=IN_PROGRESS",
    },
    {
      label: "Critical Priority",
      value: stats?.critical_priority ?? 0,
      icon: <Flame className="w-5 h-5 text-rose-500" />,
      bg: "bg-rose-500/10 border-rose-500/20",
      description: "Requires immediate attention",
      href: "/work-items?priority=CRITICAL",
    },
    {
      label: "Assigned to You",
      value: stats?.assigned_to_me ?? 0,
      icon: <UserCheck className="w-5 h-5 text-emerald-400" />,
      bg: "bg-emerald-500/10 border-emerald-500/20",
      description: "Your active responsibilities",
      href: `/work-items?assignee_id=${user?.id}`,
    },
    {
      label: "Awaiting Action / Blocked",
      value: stats?.awaiting_action_blocked ?? 0,
      icon: <AlertTriangle className="w-5 h-5 text-purple-400" />,
      bg: "bg-purple-500/10 border-purple-500/20",
      description: "Pending resolution/unblock",
      href: "/work-items?status=BLOCKED",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Operations Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time status, workload distribution, and audit history.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadStats}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 text-sm font-medium transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          <Link
            href="/work-items/new"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg shadow-indigo-600/20 transition active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create Work Item</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={loadStats} className="underline text-xs">
            Try again
          </button>
        </div>
      )}

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {statCards.map((card, idx) => (
          <Link
            key={idx}
            href={card.href}
            className={`p-5 rounded-2xl border ${card.bg} bg-slate-900/60 backdrop-blur-sm hover:scale-[1.02] transition shadow-lg group flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {card.label}
              </span>
              <div className="p-2 rounded-xl bg-slate-900/80 border border-slate-800">
                {card.icon}
              </div>
            </div>

            <div className="my-3">
              <div className="text-3xl font-extrabold text-white">
                {loading ? "..." : card.value}
              </div>
              <div className="text-xs text-slate-400 mt-1">{card.description}</div>
            </div>

            <div className="flex items-center gap-1 text-xs text-indigo-400 font-medium group-hover:translate-x-1 transition">
              <span>View details</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>
        ))}
      </div>

      {/* Main Grid: Distribution & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Status & Priority Distributions */}
        <div className="lg:col-span-1 space-y-6">
          {/* Status Breakdown */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4">
            <h2 className="text-base font-semibold text-slate-200">Status Distribution</h2>
            <div className="space-y-3">
              {[
                { status: "OPEN" as const, count: stats?.by_status?.OPEN || 0 },
                { status: "IN_PROGRESS" as const, count: stats?.by_status?.IN_PROGRESS || 0 },
                { status: "BLOCKED" as const, count: stats?.by_status?.BLOCKED || 0 },
                { status: "RESOLVED" as const, count: stats?.by_status?.RESOLVED || 0 },
              ].map((item) => {
                const total = stats?.total_work_items || 1;
                const percent = Math.round((item.count / total) * 100);
                return (
                  <div key={item.status} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <StatusBadge status={item.status} size="sm" />
                      <span className="font-semibold text-slate-300">
                        {item.count} ({percent}%)
                      </span>
                    </div>
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Priority Breakdown */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4">
            <h2 className="text-base font-semibold text-slate-200">Priority Breakdown</h2>
            <div className="space-y-3">
              {[
                { priority: "CRITICAL" as const, count: stats?.by_priority?.CRITICAL || 0 },
                { priority: "HIGH" as const, count: stats?.by_priority?.HIGH || 0 },
                { priority: "MEDIUM" as const, count: stats?.by_priority?.MEDIUM || 0 },
                { priority: "LOW" as const, count: stats?.by_priority?.LOW || 0 },
              ].map((item) => (
                <div key={item.priority} className="flex items-center justify-between text-xs py-1 border-b border-slate-800/50 last:border-0">
                  <PriorityBadge priority={item.priority} size="sm" />
                  <span className="font-semibold text-slate-300">{item.count} items</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Operational Audit History Stream */}
        <div className="lg:col-span-2 p-6 rounded-2xl border border-slate-800 bg-slate-900/50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-200">
              Recent Operational Activity
            </h2>
            <Link
              href="/work-items"
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition"
            >
              Browse all items &rarr;
            </Link>
          </div>

          <ActivityTimeline activities={stats?.recent_activities || []} />
        </div>
      </div>
    </div>
  );
}
