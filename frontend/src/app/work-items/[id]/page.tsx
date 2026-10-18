"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { fetchApi, generateIdempotencyKey } from "@/lib/api";
import {
  WorkItem,
  WorkItemStatus,
  WorkItemPriority,
  User,
  Comment,
} from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { PriorityBadge } from "@/components/PriorityBadge";
import { TypeBadge } from "@/components/TypeBadge";
import { ActivityTimeline } from "@/components/ActivityTimeline";
import {
  ArrowLeft,
  Calendar,
  Clock,
  UserCircle,
  Users,
  MessageSquare,
  Send,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  HandMetal,
  Edit2,
  ShieldAlert,
} from "lucide-react";

export default function WorkItemDetailPage() {
  const router = useRouter();
  const routeParams = useParams();
  const itemId = Number(routeParams?.id);
  const { user, loading: authLoading, isAdmin, isManager } = useAuth();

  const [item, setItem] = useState<WorkItem | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Comment input
  const [commentText, setCommentText] = useState("");

  // Edit fields
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editPriority, setEditPriority] = useState<WorkItemPriority>("LOW");

  const loadItem = async () => {
    setLoading(true);
    setError(null);
    setConflictError(null);
    try {
      const data = await fetchApi<WorkItem>(`/api/work-items/${itemId}`);
      setItem(data);
      setEditTitle(data.title);
      setEditDescription(data.description || "");
      setEditPriority(data.priority);
    } catch (err: any) {
      setError(err.message || "Failed to load work item.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push("/login");
      } else {
        loadItem();
        fetchApi<User[]>("/api/users").then(setUsers).catch(() => {});
      }
    }
  }, [user, authLoading, router, itemId]);

  // Handle Status Update with Version Concurrency Control
  const handleStatusChange = async (newStatus: WorkItemStatus) => {
    if (!item) return;
    setActionLoading(true);
    setError(null);
    setConflictError(null);
    setSuccessMessage(null);

    const idempotencyKey = generateIdempotencyKey("status-change");

    try {
      const updated = await fetchApi<WorkItem>(`/api/work-items/${item.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status: newStatus,
          version: item.version, // optimistic concurrency check
        }),
        idempotencyKey,
      });

      setItem(updated);
      setSuccessMessage(`Status updated to ${newStatus}.`);
    } catch (err: any) {
      if (err.status === 409) {
        setConflictError(
          err.message || "Conflict: This work item has been modified by another user. Please refresh."
        );
      } else {
        setError(err.message || "Failed to change status.");
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Claiming unassigned item (Concurrent Assignment Reliability Behaviour)
  const handleClaim = async () => {
    if (!item) return;
    setActionLoading(true);
    setError(null);
    setConflictError(null);
    setSuccessMessage(null);

    const idempotencyKey = generateIdempotencyKey("claim-item");

    try {
      const updated = await fetchApi<WorkItem>(`/api/work-items/${item.id}/claim`, {
        method: "POST",
        body: JSON.stringify({
          version: item.version,
        }),
        idempotencyKey,
      });

      setItem(updated);
      setSuccessMessage("You have successfully claimed this work item!");
    } catch (err: any) {
      if (err.status === 409) {
        setConflictError(
          err.message || "Conflict: This work item was just claimed or modified by another user!"
        );
      } else {
        setError(err.message || "Failed to claim work item.");
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Assign / Reassign (Manager/Admin)
  const handleAssign = async (targetAssigneeId: number | null) => {
    if (!item) return;
    setActionLoading(true);
    setError(null);
    setConflictError(null);
    setSuccessMessage(null);

    const idempotencyKey = generateIdempotencyKey("assign-item");

    try {
      const updated = await fetchApi<WorkItem>(`/api/work-items/${item.id}/assign`, {
        method: "PATCH",
        body: JSON.stringify({
          assignee_id: targetAssigneeId,
          version: item.version,
        }),
        idempotencyKey,
      });

      setItem(updated);
      setSuccessMessage("Assignee updated successfully.");
    } catch (err: any) {
      if (err.status === 409) {
        setConflictError(err.message || "Conflict: Stale update rejected. Please refresh.");
      } else {
        setError(err.message || "Failed to reassign work item.");
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Edit Save (Title, Description, Priority)
  const handleSaveEdit = async () => {
    if (!item) return;
    setActionLoading(true);
    setError(null);
    setConflictError(null);
    setSuccessMessage(null);

    const idempotencyKey = generateIdempotencyKey("edit-item");

    try {
      const updated = await fetchApi<WorkItem>(`/api/work-items/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title: editTitle.trim(),
          description: editDescription.trim() || null,
          priority: editPriority,
          version: item.version, // Concurrency control check!
        }),
        idempotencyKey,
      });

      setItem(updated);
      setIsEditing(false);
      setSuccessMessage("Work item updated successfully.");
    } catch (err: any) {
      if (err.status === 409) {
        setConflictError(
          err.message || "Conflict: Work item was modified by another user. Your changes were not saved."
        );
      } else {
        setError(err.message || "Failed to save edits.");
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Add Comment
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim() || !item) return;

    setActionLoading(true);
    setError(null);

    try {
      await fetchApi<Comment>(`/api/work-items/${item.id}/comments`, {
        method: "POST",
        body: JSON.stringify({ content: commentText.trim() }),
      });

      setCommentText("");
      // Reload full item to get updated comments and activity log
      await loadItem();
    } catch (err: any) {
      setError(err.message || "Failed to post comment.");
    } finally {
      setActionLoading(false);
    }
  };

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return "None";
    try {
      return new Date(isoString).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return isoString;
    }
  };

  if (loading || !item) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-400">Loading work item details...</p>
        </div>
      </div>
    );
  }

  const isAssignedToMe = item.assignee_id === user?.id;
  const canManage = isAdmin || isManager;

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <Link
            href="/work-items"
            className="p-2 rounded-xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-slate-400">ITEM #{item.id}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                Version {item.version}
              </span>
              <TypeBadge type={item.item_type} />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight mt-0.5">
              {item.title}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadItem}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-medium transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>

          {!isEditing && (canManage || isAssignedToMe) && (
            <button
              onClick={() => setIsEditing(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-medium transition"
            >
              <Edit2 className="w-3.5 h-3.5" />
              <span>Edit Item</span>
            </button>
          )}
        </div>
      </div>

      {/* Prominent Concurrency Conflict Alert Banner */}
      {conflictError && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border-2 border-amber-500/40 text-amber-300 shadow-xl space-y-2">
          <div className="flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-bold text-amber-200">
                Optimistic Concurrency Conflict (HTTP 409)
              </h3>
              <p className="text-xs text-amber-300/90 mt-0.5">{conflictError}</p>
            </div>
          </div>
          <div className="pt-2 flex justify-end">
            <button
              onClick={loadItem}
              className="px-4 py-1.5 rounded-lg bg-amber-500 text-slate-950 font-semibold text-xs hover:bg-amber-400 transition"
            >
              Reload Latest Server Version
            </button>
          </div>
        </div>
      )}

      {error && !conflictError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Description, Comments, and Edit Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Main Content / Edit Form */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4 shadow-xl">
            {isEditing ? (
              <div className="space-y-4">
                <h2 className="text-sm font-semibold text-slate-300">Edit Work Item</h2>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Title</label>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">
                    Description
                  </label>
                  <textarea
                    rows={4}
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Priority</label>
                  <select
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value as WorkItemPriority)}
                    className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:border-indigo-500"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>

                <div className="flex items-center gap-2 pt-2">
                  <button
                    onClick={handleSaveEdit}
                    disabled={actionLoading}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow transition"
                  >
                    {actionLoading ? "Saving..." : "Save Changes"}
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-4 py-2 rounded-xl border border-slate-800 bg-slate-800/80 text-slate-300 text-xs font-medium hover:bg-slate-800 transition"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                    Description &amp; Specifications
                  </span>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={item.status} />
                    <PriorityBadge priority={item.priority} />
                  </div>
                </div>

                <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {item.description || (
                    <span className="text-slate-500 italic">No description provided.</span>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Workflow Status Controls */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Workflow Status Progression
            </h2>
            <p className="text-xs text-slate-500">
              Allowed transitions are validated by backend state rules with optimistic concurrency control.
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-2">
              <button
                onClick={() => handleStatusChange("OPEN")}
                disabled={actionLoading || item.status === "OPEN"}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition ${
                  item.status === "OPEN"
                    ? "bg-sky-500/20 border-sky-500/40 text-sky-300 cursor-default"
                    : "border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-400"
                }`}
              >
                Mark as Open
              </button>

              <button
                onClick={() => handleStatusChange("IN_PROGRESS")}
                disabled={actionLoading || item.status === "IN_PROGRESS"}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition ${
                  item.status === "IN_PROGRESS"
                    ? "bg-amber-500/20 border-amber-500/40 text-amber-300 cursor-default"
                    : "border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-400"
                }`}
              >
                Start In Progress
              </button>

              <button
                onClick={() => handleStatusChange("BLOCKED")}
                disabled={actionLoading || item.status === "BLOCKED"}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition ${
                  item.status === "BLOCKED"
                    ? "bg-rose-500/20 border-rose-500/40 text-rose-300 cursor-default"
                    : "border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-400"
                }`}
              >
                Set Blocked
              </button>

              <button
                onClick={() => handleStatusChange("RESOLVED")}
                disabled={actionLoading || item.status === "RESOLVED"}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition ${
                  item.status === "RESOLVED"
                    ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300 cursor-default"
                    : "border-slate-800 bg-slate-950 hover:bg-slate-800 text-slate-400"
                }`}
              >
                Mark Resolved
              </button>
            </div>
          </div>

          {/* Comments Section */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <MessageSquare className="w-4 h-4 text-purple-400" />
              <span>Comments ({item.comments?.length || 0})</span>
            </div>

            {/* Post comment form */}
            <form onSubmit={handleAddComment} className="flex gap-2">
              <input
                type="text"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Add an operational note or status update..."
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 transition"
              />
              <button
                type="submit"
                disabled={actionLoading || !commentText.trim()}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50 transition"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Post</span>
              </button>
            </form>

            {/* Comments list */}
            <div className="space-y-3 pt-2">
              {item.comments && item.comments.length > 0 ? (
                item.comments.map((comment) => (
                  <div
                    key={comment.id}
                    className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300">
                        {comment.author ? comment.author.full_name : `User #${comment.author_id}`}
                      </span>
                      <span className="text-slate-500">{formatDate(comment.created_at)}</span>
                    </div>
                    <p className="text-xs text-slate-300 whitespace-pre-wrap">{comment.content}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 italic py-2">
                  No comments yet. Be the first to add context.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Right 1 Col: Metadata, Claiming, and Activity Log */}
        <div className="space-y-6">
          {/* Metadata Card */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Operational Attributes
            </h2>

            <div className="space-y-3 text-xs">
              {/* Assignee & Claim Action */}
              <div className="py-2 border-b border-slate-800/60">
                <span className="text-slate-500 block mb-1">Assignee</span>
                <div className="flex items-center justify-between">
                  {item.assignee ? (
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-indigo-400">
                        {item.assignee.full_name.charAt(0).toUpperCase()}
                      </div>
                      <span className="font-semibold text-slate-200">
                        {item.assignee.full_name}
                      </span>
                    </div>
                  ) : (
                    <span className="text-amber-400/90 font-medium italic">
                      Unassigned (Available)
                    </span>
                  )}

                  {!item.assignee && (
                    <button
                      onClick={handleClaim}
                      disabled={actionLoading}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow transition active:scale-95"
                    >
                      <HandMetal className="w-3.5 h-3.5" />
                      <span>Claim Task</span>
                    </button>
                  )}
                </div>

                {/* Manager / Admin Reassign Dropdown */}
                {canManage && (
                  <div className="mt-2 pt-2 border-t border-slate-800/40">
                    <label className="text-[10px] text-slate-400 block mb-1">
                      Reassign to Member:
                    </label>
                    <select
                      value={item.assignee_id || ""}
                      onChange={(e) =>
                        handleAssign(e.target.value ? Number(e.target.value) : null)
                      }
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                    >
                      <option value="">Unassigned</option>
                      {users.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.full_name} ({u.role})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Team */}
              <div className="py-2 border-b border-slate-800/60 flex items-center justify-between">
                <span className="text-slate-500">Team</span>
                <span className="font-medium text-slate-300">
                  {item.team ? item.team.name : `Team #${item.team_id}`}
                </span>
              </div>

              {/* Reporter */}
              <div className="py-2 border-b border-slate-800/60 flex items-center justify-between">
                <span className="text-slate-500">Reporter</span>
                <span className="font-medium text-slate-300">
                  {item.reporter ? item.reporter.full_name : `User #${item.reporter_id}`}
                </span>
              </div>

              {/* Due Date */}
              <div className="py-2 border-b border-slate-800/60 flex items-center justify-between">
                <span className="text-slate-500">Due Date</span>
                <span className="font-medium text-slate-300">{formatDate(item.due_date)}</span>
              </div>

              {/* Concurrency Version */}
              <div className="py-2 border-b border-slate-800/60 flex items-center justify-between">
                <span className="text-slate-500">Concurrency Version</span>
                <span className="font-mono text-indigo-400 font-semibold">
                  v{item.version}
                </span>
              </div>

              {/* Last Updated */}
              <div className="py-2 flex items-center justify-between">
                <span className="text-slate-500">Last Modified</span>
                <span className="font-medium text-slate-300">{formatDate(item.updated_at)}</span>
              </div>
            </div>
          </div>

          {/* Chronological Activity History */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50">
            <ActivityTimeline activities={item.activity_logs || []} />
          </div>
        </div>
      </div>
    </div>
  );
}
