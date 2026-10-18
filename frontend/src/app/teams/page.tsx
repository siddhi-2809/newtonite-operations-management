"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { fetchApi } from "@/lib/api";
import { Team, User, TeamMembership } from "@/types";
import {
  Users,
  Shield,
  PlusCircle,
  UserPlus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Lock,
} from "lucide-react";

export default function TeamsPage() {
  const router = useRouter();
  const { user, loading: authLoading, isAdmin } = useAuth();

  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Create Team modal state
  const [showCreateTeam, setShowCreateTeam] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [newTeamDescription, setNewTeamDescription] = useState("");
  const [createLoading, setCreateLoading] = useState(false);

  // Add Member state
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [memberUserId, setMemberUserId] = useState<number | "">("");
  const [memberRole, setMemberRole] = useState("MEMBER");
  const [addMemberLoading, setAddMemberLoading] = useState(false);

  const loadTeamsAndUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const [teamsData, usersData] = await Promise.all([
        fetchApi<Team[]>("/api/teams"),
        fetchApi<User[]>("/api/users"),
      ]);
      setTeams(teamsData);
      setUsers(usersData);
    } catch (err: any) {
      setError(err.message || "Failed to load team data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      if (!user) {
        router.push("/login");
      } else {
        loadTeamsAndUsers();
      }
    }
  }, [user, authLoading, router]);

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTeamName.trim()) return;

    setCreateLoading(true);
    setError(null);

    try {
      await fetchApi<Team>("/api/teams", {
        method: "POST",
        body: JSON.stringify({
          name: newTeamName.trim(),
          description: newTeamDescription.trim() || null,
        }),
      });

      setSuccess(`Team "${newTeamName}" created successfully.`);
      setShowCreateTeam(false);
      setNewTeamName("");
      setNewTeamDescription("");
      loadTeamsAndUsers();
    } catch (err: any) {
      setError(err.message || "Failed to create team.");
    } finally {
      setCreateLoading(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTeamId || !memberUserId) return;

    setAddMemberLoading(true);
    setError(null);

    try {
      await fetchApi<TeamMembership>(`/api/teams/${selectedTeamId}/members`, {
        method: "POST",
        body: JSON.stringify({
          user_id: Number(memberUserId),
          team_role: memberRole,
        }),
      });

      setSuccess("Team member added successfully.");
      setSelectedTeamId(null);
      setMemberUserId("");
      loadTeamsAndUsers();
    } catch (err: any) {
      setError(err.message || "Failed to add team member.");
    } finally {
      setAddMemberLoading(false);
    }
  };

  const handleRemoveMember = async (teamId: number, memberUserIdToRemove: number) => {
    if (!confirm("Are you sure you want to remove this member from the team?")) return;

    setError(null);
    try {
      await fetchApi(`/api/teams/${teamId}/members/${memberUserIdToRemove}`, {
        method: "DELETE",
      });
      setSuccess("Team member removed.");
      loadTeamsAndUsers();
    } catch (err: any) {
      setError(err.message || "Failed to remove team member.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            Team Administration
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage organizational divisions, member assignments, and access policies.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadTeamsAndUsers}
            disabled={loading}
            className="p-2.5 rounded-xl border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>

          {isAdmin ? (
            <button
              onClick={() => setShowCreateTeam(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg shadow-indigo-600/20 active:scale-95 transition"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Create New Team</span>
            </button>
          ) : (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
              <Lock className="w-3.5 h-3.5 text-slate-500" />
              <span>Admin-Only Management</span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{success}</span>
          </div>
          <button onClick={() => setSuccess(null)} className="text-xs underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Create Team Modal */}
      {showCreateTeam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md p-6 rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl space-y-4">
            <h2 className="text-lg font-bold text-white">Create New Team</h2>
            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Team Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newTeamName}
                  onChange={(e) => setNewTeamName(e.target.value)}
                  placeholder="e.g. SRE &amp; Observability"
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={newTeamDescription}
                  onChange={(e) => setNewTeamDescription(e.target.value)}
                  placeholder="Mandate, responsibilities, and operational scope..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateTeam(false)}
                  className="px-4 py-2 rounded-xl border border-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow"
                >
                  {createLoading ? "Creating..." : "Create Team"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Member Modal */}
      {selectedTeamId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md p-6 rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl space-y-4">
            <h2 className="text-lg font-bold text-white">Add Member to Team</h2>
            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Select User <span className="text-rose-400">*</span>
                </label>
                <select
                  required
                  value={memberUserId}
                  onChange={(e) => setMemberUserId(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Choose User</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email} - {u.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Team Role
                </label>
                <select
                  value={memberRole}
                  onChange={(e) => setMemberRole(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="MEMBER">Member</option>
                  <option value="LEAD">Team Lead</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedTeamId(null)}
                  className="px-4 py-2 rounded-xl border border-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addMemberLoading}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow"
                >
                  {addMemberLoading ? "Adding..." : "Add to Team"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Teams Grid */}
      {loading ? (
        <div className="py-20 text-center">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-400">Loading teams and memberships...</p>
        </div>
      ) : teams.length === 0 ? (
        <div className="py-16 text-center text-slate-400">No teams found.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {teams.map((team) => (
            <div
              key={team.id}
              className="p-6 rounded-2xl border border-slate-800 bg-slate-900/50 space-y-4 shadow-xl flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                      <Users className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-white tracking-tight">{team.name}</h2>
                      <span className="text-xs text-slate-500">
                        {team.memberships?.length || 0} active members
                      </span>
                    </div>
                  </div>

                  {isAdmin && (
                    <button
                      onClick={() => setSelectedTeamId(team.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 text-xs font-medium transition"
                    >
                      <UserPlus className="w-3.5 h-3.5" />
                      <span>Add Member</span>
                    </button>
                  )}
                </div>

                <p className="text-xs text-slate-400 mt-3 leading-relaxed">
                  {team.description || "No description specified."}
                </p>

                {/* Member roster */}
                <div className="mt-5 pt-4 border-t border-slate-800/80 space-y-2">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Team Members
                  </div>

                  {team.memberships && team.memberships.length > 0 ? (
                    <div className="space-y-1.5">
                      {team.memberships.map((m) => (
                        <div
                          key={m.id}
                          className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800/60 text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-indigo-400">
                              {m.user?.full_name.charAt(0).toUpperCase() || "?"}
                            </div>
                            <div>
                              <span className="font-medium text-slate-200">
                                {m.user ? m.user.full_name : `User #${m.user_id}`}
                              </span>
                              <span className="text-[10px] text-slate-500 ml-1.5">
                                ({m.team_role})
                              </span>
                            </div>
                          </div>

                          {isAdmin && (
                            <button
                              onClick={() => handleRemoveMember(team.id, m.user_id)}
                              title="Remove from team"
                              className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic py-1">
                      No members assigned to this team yet.
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
