"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { api } from "@/lib/api";
import { Bus, Lock, User } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await api.post("/auth/token", {
        username,
        password,
      });

      Cookies.set("token", response.data.access_token, { expires: 1 }); // 1 day
      router.push("/");
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg).join(", "));
      } else {
        setError("Failed to login. Check credentials.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass-panel p-8 rounded-2xl w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="bg-primary/20 p-3 rounded-full mb-4">
            <Bus className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold">Smart-Transit Admin</h1>
          <p className="text-gray-400 mt-2 text-sm">Enter your credentials to access the fleet dashboard.</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Username</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-gray-500" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="block w-full pl-10 pr-3 py-2 border border-border rounded-lg bg-input text-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                placeholder="admin"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-gray-500" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="block w-full pl-10 pr-3 py-2 border border-border rounded-lg bg-input text-white focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          {error && <div className="text-destructive text-sm text-center bg-destructive/10 p-2 rounded">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-primary hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary focus:ring-offset-background disabled:opacity-50 transition-all"
          >
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
