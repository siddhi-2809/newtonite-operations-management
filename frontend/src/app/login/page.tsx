"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Lock, Mail, AlertCircle, ArrowRight, ShieldCheck, UserCheck, Briefcase } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      router.push("/");
    } catch (err: any) {
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const fillCredentials = (userEmail: string, userPass: string) => {
    setEmail(userEmail);
    setPassword(userPass);
    setError(null);
  };

  return (
    <div className="min-h-[75vh] flex items-center justify-center">
      <div className="w-full max-w-md p-8 rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl shadow-2xl shadow-indigo-950/20">
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/10 border border-indigo-500/30 text-indigo-400 mb-4">
            <Lock className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Sign In to Newtonite</h1>
          <p className="text-sm text-slate-400 mt-1">
            Operations Management &amp; Reliability Platform
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@newtonite.io"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/25 active:scale-[0.99] transition disabled:opacity-50"
          >
            {loading ? (
              <span className="inline-block animate-spin mr-2">⟳</span>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Quick evaluation personas */}
        <div className="mt-8 pt-6 border-t border-slate-800/80">
          <div className="text-xs font-medium text-slate-400 mb-3 text-center">
            Quick Persona Login (Dev / Assessment)
          </div>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => fillCredentials("admin@newtonite.io", "AdminSecure123!")}
              className="p-2.5 rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800/60 text-left transition group"
            >
              <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-400">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Admin</span>
              </div>
              <div className="text-[10px] text-slate-500 truncate mt-0.5">admin@newtonite.io</div>
            </button>

            <button
              type="button"
              onClick={() => fillCredentials("manager@newtonite.io", "ManagerPass123!")}
              className="p-2.5 rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800/60 text-left transition group"
            >
              <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400">
                <Briefcase className="w-3.5 h-3.5" />
                <span>Manager</span>
              </div>
              <div className="text-[10px] text-slate-500 truncate mt-0.5">manager@newtonite.io</div>
            </button>

            <button
              type="button"
              onClick={() => fillCredentials("member@newtonite.io", "MemberPass123!")}
              className="p-2.5 rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800/60 text-left transition group"
            >
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                <UserCheck className="w-3.5 h-3.5" />
                <span>Member</span>
              </div>
              <div className="text-[10px] text-slate-500 truncate mt-0.5">member@newtonite.io</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
