"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { User } from "@/types";
import { fetchApi } from "./api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  isAdmin: boolean;
  isManager: boolean;
  isMember: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // Rehydrate auth from localStorage
    const savedToken = localStorage.getItem("newtonite_token");
    const savedUser = localStorage.getItem("newtonite_user");

    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        // Verify with /api/auth/me in background
        fetchApi<User>("/api/auth/me")
          .then((currentUser) => {
            setUser(currentUser);
            localStorage.setItem("newtonite_user", JSON.stringify(currentUser));
          })
          .catch(() => {
            // Token expired or invalid
            logout();
          })
          .finally(() => setLoading(false));
      } catch (err) {
        logout();
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const data = await fetchApi<{ access_token: string; token_type: string; user: User }>(
        "/api/auth/login",
        {
          method: "POST",
          body: JSON.stringify({ email, password }),
        }
      );

      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem("newtonite_token", data.access_token);
      localStorage.setItem("newtonite_user", JSON.stringify(data.user));
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("newtonite_token");
    localStorage.removeItem("newtonite_user");
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const currentUser = await fetchApi<User>("/api/auth/me");
      setUser(currentUser);
      localStorage.setItem("newtonite_user", JSON.stringify(currentUser));
    } catch {
      // Ignored
    }
  };

  const isAdmin = user?.role === "ADMIN";
  const isManager = user?.role === "MANAGER";
  const isMember = user?.role === "MEMBER";

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        refreshUser,
        isAdmin,
        isManager,
        isMember,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
